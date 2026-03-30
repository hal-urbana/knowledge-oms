"""
Ingest Service - Main orchestration layer
Coordinates UDL consumption, LightRAG indexing, and ArcGIS Knowledge integration
"""

import os
import logging
import threading
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from .udl_adapter import UDLAdapter, UDLProcessor, UDLMessage, create_udl_adapter_from_env
from .arcgis_knowledge_client import ArcGISKnowledgeClient, Entity, create_client_from_env
from .lightrag_indexer import LightRAGIndexer, create_indexer_from_env

logger = logging.getLogger(__name__)


@dataclass
class IngestConfig:
    """Configuration for the ingest service."""
    batch_size: int = 20
    max_retries: int = 3
    retry_delay: int = 10
    poll_interval: int = 5
    max_backlog: int = 500


@dataclass
class IngestionStats:
    """Statistics for monitoring ingestion."""
    total_messages: int = 0
    success_count: int = 0
    fail_count: int = 0
    entities_created: int = 0
    relationships_created: int = 0
    indexed_count: int = 0
    start_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return (self.success_count / total * 100) if total > 0 else 0


class IngestService:
    """
    Main ingest service coordinating the full pipeline:
    UDL → Kafka Consumer → Transformer → ArcGIS Knowledge + LightRAG
    """
    
    def __init__(
        self,
        udl_adapter: UDLAdapter,
        kg_client: ArcGISKnowledgeClient,
        rag_indexer: LightRAGIndexer,
        config: Optional[IngestConfig] = None
    ):
        """
        Initialize the ingest service.
        
        Args:
            udl_adapter: Configured UDL adapter for Kafka
            kg_client: ArcGIS Knowledge client
            rag_indexer: LightRAG indexer for semantic search
            config: Optional configuration overrides
        """
        self.udl = udl_adapter
        self.kg = kg_client
        self.rag = rag_indexer
        self.config = config or IngestConfig()
        
        self.processor = UDLProcessor()
        self.stats = IngestionStats()
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._batch_queue: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def start(self, kg_id: str) -> None:
        """
        Start the ingest service.
        
        Args:
            kg_id: Knowledge graph ID to ingest into
        """
        if self._running:
            logger.warning("Service already running")
            return
        
        self.kg_id = kg_id
        self._running = True
        self.stats.start_time = datetime.now()
        
        self.udl.connect()
        
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        logger.info(f"Ingest service started - targeting KG: {kg_id}")
    
    def stop(self) -> None:
        """Stop the ingest service gracefully."""
        if not self._running:
            return
        
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=10)
        
        self._flush_batch()
        self.udl.disconnect()
        
        logger.info("Ingest service stopped")
    
    def _run_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                self._poll_and_process()
            except Exception as e:
                logger.error(f"Error in ingest loop: {e}")
                time.sleep(self.config.retry_delay)
    
    def _poll_and_process(self) -> None:
        """Poll UDL and process messages."""
        messages = self.udl.consume_batch(
            batch_size=self.config.batch_size,
            timeout_ms=5000
        )
        
        if not messages:
            time.sleep(self.config.poll_interval)
            return
        
        for msg in messages:
            entity_data = self.processor.process_message(msg)
            if entity_data:
                with self._lock:
                    self._batch_queue.append(entity_data)
                    self.stats.total_messages += 1
        
        # Process batch if full
        with self._lock:
            if len(self._batch_queue) >= self.config.batch_size:
                self._flush_batch()
    
    def _flush_batch(self) -> None:
        """Flush queued entities to ArcGIS and LightRAG."""
        if not self._batch_queue:
            return
        
        batch = self._batch_queue[:]
        self._batch_queue = []
        
        logger.info(f"Flushing batch of {len(batch)} entities")
        
        entities = []
        for data in batch:
            try:
                entity = Entity(
                    name=data.get('name', 'Unknown'),
                    type_name=data.get('type_name', 'UDLObject'),
                    properties=data.get('properties', {})
                )
                entities.append(entity)
            except Exception as e:
                logger.warning(f"Failed to create entity: {e}")
                self.stats.fail_count += 1
        
        if entities:
            # Batch create in ArcGIS Knowledge
            try:
                created = self.kg.create_entities_batch(self.kg_id, entities)
                self.stats.entities_created += len(created)
                self.stats.success_count += len(created)
                
                # Index in LightRAG
                for entity in created:
                    if entity.entity_id:
                        self.rag.index_entity(
                            entity_id=entity.entity_id,
                            name=entity.name,
                            description=entity.properties.get('description', ''),
                            properties=entity.properties,
                            entity_type=entity.type_name
                        )
                        self.stats.indexed_count += 1
                
                logger.info(f"Successfully ingested {len(created)} entities")
                
            except Exception as e:
                logger.error(f"Failed to create entities: {e}")
                self.stats.fail_count += len(entities)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status and statistics."""
        with self._lock:
            stats = IngestionStats(
                total_messages=self.stats.total_messages,
                success_count=self.stats.success_count,
                fail_count=self.stats.fail_count,
                entities_created=self.stats.entities_created,
                relationships_created=self.stats.relationships_created,
                indexed_count=self.stats.indexed_count,
                start_time=self.stats.start_time,
                last_update=datetime.now()
            )
        
        return {
            'running': self._running,
            'kg_id': getattr(self, 'kg_id', None),
            'batch_queue_size': len(self._batch_queue),
            'statistics': {
                'total_messages': stats.total_messages,
                'success_count': stats.success_count,
                'fail_count': stats.fail_count,
                'entities_created': stats.entities_created,
                'relationships_created': stats.relationships_created,
                'indexed_count': stats.indexed_count,
                'success_rate': stats.success_rate,
                'uptime_seconds': (
                    (datetime.now() - stats.start_time).total_seconds()
                    if stats.start_time else 0
                )
            }
        }


def create_ingest_service_from_config(
    udl_host: Optional[str] = None,
    udl_topic: Optional[str] = None,
    arcgis_url: Optional[str] = None,
    arcgis_username: Optional[str] = None,
    arcgis_password: Optional[str] = None,
    knowledge_graph_name: Optional[str] = None
) -> IngestService:
    """
    Factory function to create configured IngestService from parameters.
    
    Reads defaults from environment variables.
    """
    # UDL Adapter
    if udl_host:
        from .udl_adapter import UDLConfig
        udl_config = UDLConfig(
            bootstrap_servers=udl_host,
            topic=udl_topic or os.getenv("UDL_TOPIC", "udl.primary-topic"),
            consumer_group=os.getenv("UDL_CONSUMER_GROUP", "knowledge-oms-consumer"),
            username=os.getenv("UDL_USERNAME"),
            password=os.getenv("UDL_PASSWORD"),
        )
        udl_adapter = UDLAdapter(udl_config)
    else:
        udl_adapter = create_udl_adapter_from_env()
    
    # ArcGIS Knowledge Client
    if arcgis_url:
        kg_client = ArcGISKnowledgeClient(
            portal_url=arcgis_url,
            username=arcgis_username or os.getenv("ARCGIS_USERNAME", ""),
            password=arcgis_password or os.getenv("ARCGIS_PASSWORD", ""),
            verify_ssl=os.getenv("ARCGIS_VERIFY_SSL", "true").lower() == "true"
        )
    else:
        kg_client = create_client_from_env()
    
    # LightRAG Indexer
    rag_indexer = create_indexer_from_env()
    
    return IngestService(
        udl_adapter=udl_adapter,
        kg_client=kg_client,
        rag_indexer=rag_indexer
    )
