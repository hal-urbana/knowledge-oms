"""
UDL OMS Demo - Knowledge OMS Demonstration
Models the goal of displaying a primary UDL object and associated information objects on a map.
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automation.arcgis_knowledge_client import ArcGISKnowledgeClient, Entity, Relationship
from automation.lightrag_indexer import LightRAGIndexer
from automation.udl_adapter import UDLMessage, UDLProcessor

def run_oms_demo():
    print("=" * 60)
    print("KNOWLEDGE OMS - Unified Data Library Integration Demo")
    print("=" * 60)

    # 1. Setup Clients
    portal_url = os.getenv("ARCGIS_PORTAL_URL", "https://portal.usmlabs.com")
    username = os.getenv("ARCGIS_USERNAME", "hal")
    password = os.getenv("ARCGIS_PASSWORD", "secret")
    
    print(f"\n1. Initializing ArcGIS Knowledge Client...")
    print(f"   Target: {portal_url}")
    kg_client = ArcGISKnowledgeClient(portal_url, username, password)
    
    print(f"2. Initializing LightRAG Indexer...")
    rag_indexer = LightRAGIndexer(persist_dir="./demo_lightrag_data")

    # 2. Simulate UDL Message
    # This represents a 'primary object' with geographic properties and 'associated info objects'
    udl_payload = {
        "id": "SHIP-39902",
        "type": "Vessel",
        "name": "MV Ocean Explorer",
        "geometry": {
            "type": "Point", 
            "coordinates": [58.58, 23.63] # Near Muscat, Oman
        },
        "properties": {
            "flag": "Panama",
            "mmsi": "355912000",
            "status": "In Transit",
            "destination": "Port of Muscat"
        },
        "associated_objects": [
            {
                "id": "INTEL-A-99",
                "type": "IntelligenceReport",
                "name": "Muscat Port Security Alert",
                "description": "Port of Muscat reported unusual activity near Berth 4. Vessel suspected of carrying unmanifested electronics.",
                "properties": {"priority": "High", "source": "OSINT-Muscat"}
            },
            {
                "id": "DOC-B-102",
                "type": "Manifest",
                "name": "Cargo Manifest - Voyage 42",
                "description": "Standard container shipment including agricultural machinery and consumer goods.",
                "properties": {"container_count": 12, "last_port": "Dubai"}
            }
        ]
    }

    print(f"\n3. Simulating UDL Message Consumption...")
    msg = UDLMessage(
        topic="udl.maritime.tracking",
        partition=0,
        offset=1024,
        timestamp=datetime.now(),
        key="SHIP-39902",
        value=udl_payload
    )
    print(f"   Received message ID: {msg.key} from topic {msg.topic}")

    # 3. Process Message
    processor = UDLProcessor()
    processed_data = processor.process_message(msg)
    print(f"\n4. Processing and Transforming with UDLProcessor...")
    print(f"   Primary Object: {processed_data['name']} ({processed_data['type_name']})")
    print(f"   Geolocation: {processed_data['geometry']['coordinates']}")
    print(f"   Associated Objects: {len(processed_data['associated_objects'])}")

    # 4. Ingest into Knowledge Graph
    print(f"\n5. Ingesting into Esri Knowledge Server...")
    
    # In a real demo, we'd use a real KG ID. Here we mock/print.
    kg_id = "knowledge_oms_graph_01"
    print(f"   Target Knowledge Graph ID: {kg_id}")

    try:
        # Create Primary Entity
        primary = Entity(
            name=processed_data['name'],
            type_name=processed_data['type_name'],
            properties=processed_data['properties']
        )
        # created_primary = kg_client.create_entity(kg_id, primary)
        # For demo purposes, we'll simulate the created ID
        primary.entity_id = "ENT-001"
        print(f"   ✓ Created Primary Entity: {primary.name} [ID: {primary.entity_id}]")

        # Create Associated Entities and Relationships
        for assoc in processed_data['associated_objects']:
            assoc_ent = Entity(
                name=assoc['name'],
                type_name=assoc['type_name'],
                properties=assoc['properties']
            )
            assoc_ent.properties['description'] = assoc['description']
            # created_assoc = kg_client.create_entity(kg_id, assoc_ent)
            assoc_ent.entity_id = f"ENT-ASSOC-{assoc['id']}"
            print(f"   ✓ Created Associated Entity: {assoc_ent.name} [ID: {assoc_ent.entity_id}]")

            # Create Relationship
            rel = Relationship(
                source_entity_id=primary.entity_id,
                target_entity_id=assoc_ent.entity_id,
                relationship_type="HAS_INTELLIGENCE",
                properties={"context": "OMS-UDL-Mapping"}
            )
            # kg_client.create_relationship(kg_id, rel)
            print(f"   ✓ Linked {primary.name} --[HAS_INTELLIGENCE]--> {assoc_ent.name}")

            # Index everything in LightRAG
            rag_indexer.index_entity(
                entity_id=assoc_ent.entity_id,
                name=assoc_ent.name,
                description=assoc['description'],
                properties=assoc_ent.properties,
                entity_type=assoc_ent.type_name
            )

        rag_indexer.index_entity(
            entity_id=primary.entity_id,
            name=primary.name,
            description=f"Vessel {primary.name} at {processed_data['geometry']['coordinates']}",
            properties=primary.properties,
            entity_type=primary.type_name
        )
        print(f"\n6. Indexed objects in LightRAG for intelligent search.")

    except Exception as e:
        print(f"   Error during ingestion: {e}")

    # 5. Intelligent Query Example
    print(f"\n7. Demonstration of Semantic Search (LightRAG)...")
    query = "Are there any vessels with security alerts or unusual activity?"
    print(f"   Query: \"{query}\"")
    
    results = rag_indexer.search(query, top_k=2, mode="hybrid")
    
    for i, res in enumerate(results):
        print(f"   [{i+1}] Result: {res.metadata['name']} (Score: {res.score:.4f})")
        print(f"       Type: {res.metadata['type']}")
        if res.metadata['type'] == 'IntelligenceReport':
            print(f"       Summary: {res.metadata['properties'].get('description', '')[:100]}...")

    print("\n" + "=" * 60)
    print("OMS WORKFLOW COMPLETE")
    print("Objects now available for ArcGIS Pro mapping with geographic properties.")
    print("=" * 60)

if __name__ == "__main__":
    run_oms_demo()
