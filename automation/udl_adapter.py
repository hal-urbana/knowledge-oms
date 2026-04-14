"""
UDL Adapter - Kafka Consumer for Unified Data Library
Handles message consumption from UDL Kafka topics
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from kafka import KafkaConsumer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("kafka-python not installed. UDL adapter will use mock mode.")


@dataclass
class UDLMessage:
    """Represents a message from the Unified Data Library."""
    topic: str
    partition: int
    offset: int
    timestamp: datetime
    key: Optional[str]
    value: Dict[str, Any]
    headers: Dict[str, str] = None
    
    @classmethod
    def from_kafka_record(cls, record) -> "UDLMessage":
        """Create UDLMessage from a Kafka consumer record."""
        return cls(
            topic=record.topic,
            partition=record.partition,
            offset=record.offset,
            timestamp=datetime.fromtimestamp(record.timestamp / 1000),
            key=record.key.decode('utf-8') if record.key else None,
            value=json.loads(record.value.decode('utf-8')) if isinstance(record.value, bytes) else record.value,
            headers={k: v.decode('utf-8') if v else '' for k, v in (record.headers or [])}
        )


@dataclass
class UDLConfig:
    """Configuration for UDL Kafka connection."""
    bootstrap_servers: str
    topic: str
    consumer_group: str
    username: Optional[str] = None
    password: Optional[str] = None
    security_protocol: str = "SASL_SSL"
    sasl_mechanism: str = "PLAIN"
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True
    max_poll_records: int = 100
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 10000


class UDLAdapter:
    """
    Adapter for consuming messages from Unified Data Library via Kafka.
    
    Supports:
    - SASL/SSL authentication
    - Topic subscription with pattern matching
    - Message parsing and validation
    - Batch consumption for high throughput
    """
    
    def __init__(self, config: UDLConfig):
        """
        Initialize UDL adapter with configuration.
        
        Args:
            config: UDLConfig object with connection parameters
        """
        self.config = config
        self._consumer: Optional[Any] = None
        self._connected = False
    
    def connect(self) -> None:
        """Establish connection to Kafka broker."""
        if not KAFKA_AVAILABLE:
            logger.warning("Kafka library not available - running in mock mode")
            self._connected = True
            return
        
        try:
            consumer_kwargs = {
                'bootstrap_servers': self.config.bootstrap_servers,
                'group_id': self.config.consumer_group,
                'auto_offset_reset': self.config.auto_offset_reset,
                'enable_auto_commit': self.config.enable_auto_commit,
                'max_poll_records': self.config.max_poll_records,
                'session_timeout_ms': self.config.session_timeout_ms,
                'heartbeat_interval_ms': self.config.heartbeat_interval_ms,
                'value_deserializer': lambda m: json.loads(m.decode('utf-8')),
                'key_deserializer': lambda k: k.decode('utf-8') if k else None,
            }
            
            # Add SASL authentication if configured
            if self.config.username and self.config.password:
                consumer_kwargs.update({
                    'security_protocol': self.config.security_protocol,
                    'sasl_mechanism': self.config.sasl_mechanism,
                    'sasl_plain_username': self.config.username,
                    'sasl_plain_password': self.config.password,
                })
            
            self._consumer = KafkaConsumer(self.config.topic, **consumer_kwargs)
            self._connected = True
            logger.info(f"Connected to UDL Kafka broker: {self.config.bootstrap_servers}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close Kafka consumer connection."""
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        self._connected = False
        logger.info("Disconnected from UDL")
    
    def consume(self, timeout_ms: int = 1000) -> List[UDLMessage]:
        """
        Consume messages from subscribed topics.
        
        Args:
            timeout_ms: Poll timeout in milliseconds
            
        Returns:
            List of UDLMessage objects
        """
        if not self._connected:
            self.connect()
        
        messages = []
        
        if not KAFKA_AVAILABLE or self._consumer is None:
            # Mock mode - return empty list
            return messages
        
        try:
            records = self._consumer.poll(timeout_ms=timeout_ms)
            
            for topic_partition, record_list in records.items():
                for record in record_list:
                    try:
                        messages.append(UDLMessage.from_kafka_record(record))
                    except Exception as e:
                        logger.warning(f"Failed to parse message: {e}")
                        
        except Exception as e:
            logger.error(f"Error consuming messages: {e}")
        
        return messages
    
    def consume_batch(self, batch_size: int, timeout_ms: int = 5000) -> List[UDLMessage]:
        """
        Consume a batch of messages up to batch_size.
        
        Args:
            batch_size: Maximum messages to return
            timeout_ms: Maximum time to wait for batch
            
        Returns:
            List of UDLMessage objects (may be fewer than batch_size)
        """
        messages = []
        start_time = datetime.now()
        
        while len(messages) < batch_size:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            remaining_timeout = max(timeout_ms - elapsed, 0)
            
            if remaining_timeout <= 0:
                break
                
            new_messages = self.consume(timeout_ms=int(remaining_timeout))
            messages.extend(new_messages)
            
            if not new_messages:
                break
        
        return messages[:batch_size]
    
    def subscribe(self, topics: List[str]) -> None:
        """
        Subscribe to additional topics.
        
        Args:
            topics: List of topic names or patterns
        """
        if self._consumer:
            self._consumer.subscribe(topics)
            logger.info(f"Subscribed to topics: {topics}")
    
    @property
    def is_connected(self) -> bool:
        """Check if adapter is connected to broker."""
        return self._connected


class UDLProcessor:
    """
    Processes UDL messages and transforms them for knowledge graph ingestion.
    
    Handles:
    - Message schema validation
    - Data transformation to entity format
    - Geographic property extraction
    - Relationship resolution
    """
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
    
    def validate_message(self, message: UDLMessage) -> bool:
        """
        Validate message schema and required fields.
        
        Args:
            message: UDLMessage to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['type', 'id']
        
        for field in required_fields:
            if field not in message.value:
                logger.warning(f"Message missing required field: {field}")
                return False
        
        return True
    
    def extract_entity_properties(self, message: UDLMessage) -> Dict[str, Any]:
        """
        Extract properties from UDL message for entity creation.
        
        Args:
            message: UDLMessage containing data
            
        Returns:
            Dictionary of entity properties
        """
        data = message.value
        
        properties = {
            'udl_id': data.get('id', ''),
            'udl_type': data.get('type', ''),
            'udl_topic': message.topic,
            'udl_timestamp': message.timestamp.isoformat(),
        }
        
        # Copy all data fields
        if 'properties' in data:
            properties.update(data['properties'])
        
        # Handle geographic data
        if 'geometry' in data:
            properties['geometry'] = data['geometry']
        
        # Handle metadata
        if 'metadata' in data:
            properties['metadata'] = data['metadata']
        
        return properties
    
    def extract_geographic_properties(self, message: UDLMessage) -> Optional[Dict[str, Any]]:
        """
        Extract geographic properties for ArcGIS mapping.
        
        Args:
            message: UDLMessage with potential geometry
            
        Returns:
            GeoJSON geometry dict or None
        """
        data = message.value
        
        if 'geometry' in data:
            return data['geometry']
        
        if 'location' in data:
            loc = data['location']
            if isinstance(loc, dict) and ('lat' in loc or 'latitude' in loc):
                return {
                    'type': 'Point',
                    'coordinates': [
                        loc.get('lon', loc.get('longitude', 0)),
                        loc.get('lat', loc.get('latitude', 0))
                    ]
                }
        
        return None
    
    def process_message(self, message: UDLMessage) -> Optional[Dict[str, Any]]:
        """
        Process a single UDL message into entity-ready format.
        
        Args:
            message: UDLMessage to process
            
        Returns:
            Dict with entity data or None if invalid
        """
        if not self.validate_message(message):
            self.error_count += 1
            return None
        
        entity_data = {
            'id': message.value.get('id'),
            'name': message.value.get('name', message.value.get('id', 'Unknown')),
            'type_name': message.value.get('type', 'UDLObject'),
            'properties': self.extract_entity_properties(message),
        }
        
        geo = self.extract_geographic_properties(message)
        if geo:
            entity_data['geometry'] = geo
            # Ensure geometry is in properties as well for Knowledge Server
            entity_data['properties']['Shape'] = geo
        
        # Extract associated objects
        associated = []
        if 'associated_objects' in message.value:
            for obj in message.value['associated_objects']:
                if 'id' in obj and 'type' in obj:
                    associated.append({
                        'id': obj.get('id'),
                        'name': obj.get('name', obj.get('id')),
                        'type_name': obj.get('type'),
                        'properties': obj.get('properties', {}),
                        'description': obj.get('description', '')
                    })
        
        entity_data['associated_objects'] = associated
        
        self.processed_count += 1
        return entity_data
    
    def process_batch(self, messages: List[UDLMessage]) -> List[Dict[str, Any]]:
        """
        Process multiple messages.
        
        Args:
            messages: List of UDLMessage objects
            
        Returns:
            List of processed entity data dicts
        """
        results = []
        
        for msg in messages:
            result = self.process_message(msg)
            if result:
                results.append(result)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            'processed': self.processed_count,
            'errors': self.error_count,
            'success_rate': (
                self.processed_count / (self.processed_count + self.error_count)
                if (self.processed_count + self.error_count) > 0
                else 0
            )
        }


def create_udl_adapter_from_env() -> UDLAdapter:
    """
    Factory to create UDLAdapter from environment variables.
    """
    config = UDLConfig(
        bootstrap_servers=os.getenv("UDL_BOOTSTRAP_SERVERS", "localhost:9092"),
        topic=os.getenv("UDL_TOPIC", "udl.primary-topic"),
        consumer_group=os.getenv("UDL_CONSUMER_GROUP", "knowledge-oms-consumer"),
        username=os.getenv("UDL_USERNAME"),
        password=os.getenv("UDL_PASSWORD"),
        security_protocol=os.getenv("UDL_SECURITY_PROTOCOL", "SASL_SSL"),
        sasl_mechanism=os.getenv("UDL_SASL_MECHANISM", "PLAIN"),
    )
    
    return UDLAdapter(config)
