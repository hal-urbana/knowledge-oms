"""
Example: Create a Knowledge Graph and Add Entities
Demonstrates basic usage of the Knowledge OMS ArcGIS client
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automation.arcgis_knowledge_client import ArcGISKnowledgeClient, Entity


def create_facility_knowledge_graph():
    """
    Example: Create a facility management knowledge graph with
    buildings, rooms, sensors, and their relationships.
    """
    # Initialize client from environment or hardcoded values
    client = ArcGISKnowledgeClient(
        portal_url=os.getenv("ARCGIS_PORTAL_URL", "https://your-portal.arcgis.com"),
        username=os.getenv("ARCGIS_USERNAME", "your-username"),
        password=os.getenv("ARCGIS_PASSWORD", "your-password"),
        verify_ssl=True
    )
    
    print("=" * 60)
    print("Creating Facility Management Knowledge Graph")
    print("=" * 60)
    
    # Create knowledge graph
    kg = client.create_knowledge_graph(
        title="Facility Management KG",
        description="Knowledge graph for building and room management",
        tags=["facility", "management", "iot"]
    )
    kg_id = kg.get('knowledgeId', kg.get('id'))
    print(f"\n✓ Created knowledge graph: {kg_id}")
    
    # Define entities
    building = Entity(
        name="Building A",
        type_name="Building",
        properties={
            "address": "123 Main St",
            "floors": 3,
            "sqft": 50000,
            "year_built": 2010
        }
    )
    
    room1 = Entity(
        name="Room 101",
        type_name="Room",
        properties={
            "floor": 1,
            "capacity": 20,
            "type": "office"
        }
    )
    
    room2 = Entity(
        name="Room 102",
        type_name="Room",
        properties={
            "floor": 1,
            "capacity": 8,
            "type": "conference"
        }
    )
    
    sensor1 = Entity(
        name="Temperature Sensor S1",
        type_name="Sensor",
        properties={
            "sensor_type": "temperature",
            "unit": "fahrenheit",
            "location": "Room 101"
        }
    )
    
    # Batch create entities
    print("\nCreating entities...")
    entities = client.create_entities_batch(kg_id, [building, room1, room2, sensor1])
    
    for entity in entities:
        print(f"  ✓ {entity.name} ({entity.type_name}) - ID: {entity.entity_id}")
    
    # Create relationships
    print("\nCreating relationships...")
    
    from automation.arcgis_knowledge_client import Relationship
    
    rel1 = Relationship(
        source_entity_id=entities[1].entity_id,  # Room 101
        target_entity_id=entities[0].entity_id,  # Building A
        relationship_type="CONTAINS",
        properties={}
    )
    
    rel2 = Relationship(
        source_entity_id=entities[2].entity_id,  # Room 102
        target_entity_id=entities[0].entity_id,  # Building A
        relationship_type="CONTAINS",
        properties={}
    )
    
    rel3 = Relationship(
        source_entity_id=entities[3].entity_id,  # Sensor S1
        target_entity_id=entities[1].entity_id,  # Room 101
        relationship_type="MONITORS",
        properties={}
    )
    
    for rel in [rel1, rel2, rel3]:
        created = client.create_relationship(kg_id, rel)
        print(f"  ✓ {rel.relationship_type} relationship created")
    
    print("\n" + "=" * 60)
    print("Knowledge graph created successfully!")
    print(f"Knowledge Graph ID: {kg_id}")
    print("=" * 60)
    
    return kg_id


def search_example(kg_id: str):
    """Example: Search for entities in knowledge graph."""
    client = ArcGISKnowledgeClient(
        portal_url=os.getenv("ARCGIS_PORTAL_URL", "https://your-portal.arcgis.com"),
        username=os.getenv("ARCGIS_USERNAME", "your-username"),
        password=os.getenv("ARCGIS_PASSWORD", "your-password"),
    )
    
    print("\nSearching for 'room'...")
    results = client.search_entities(kg_id, "room", limit=10)
    
    for result in results:
        print(f"  - {result.get('name', 'Unknown')} ({result.get('typeName', 'Unknown')})")


if __name__ == "__main__":
    # Check for credentials
    if not os.getenv("ARCGIS_PORTAL_URL"):
        print("⚠️  Set ARCGIS_PORTAL_URL, ARCGIS_USERNAME, ARCGIS_PASSWORD environment variables")
        print("   Using placeholder values for demonstration...")
    
    kg_id = create_facility_knowledge_graph()
    
    # Uncomment to run search example
    # search_example(kg_id)
