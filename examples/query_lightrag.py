"""
Example: Query LightRAG Index
Demonstrates semantic search over indexed entities
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automation.lightrag_indexer import LightRAGIndexer


def main():
    # Create indexer
    indexer = LightRAGIndexer(
        persist_dir="./lightrag_data",
        embedding_dim=1536
    )
    
    print("=" * 60)
    print("LightRAG Semantic Search Example")
    print("=" * 60)
    
    # Index sample entities
    entities = [
        {
            "id": "bldg-001",
            "name": "Building A",
            "description": "Main office building with 3 floors. Contains conference rooms and open office space.",
            "type": "Building",
            "properties": {"floors": 3, "sqft": 50000}
        },
        {
            "id": "room-101",
            "name": "Conference Room Alpha",
            "description": "Large conference room on floor 1. Equipped with video conferencing.",
            "type": "Room",
            "properties": {"capacity": 20, "floor": 1}
        },
        {
            "id": "sensor-temp-001",
            "name": "Temperature Sensor",
            "description": "IoT sensor monitoring temperature in Room 101",
            "type": "Sensor",
            "properties": {"reading": 72, "unit": "F"}
        },
        {
            "id": "person-001",
            "name": "John Smith",
            "description": "Facilities manager. Responsible for building operations.",
            "type": "Person",
            "properties": {"role": "Manager", "department": "Facilities"}
        }
    ]
    
    print("\nIndexing sample entities...")
    for ent in entities:
        indexer.index_entity(
            entity_id=ent["id"],
            name=ent["name"],
            description=ent["description"],
            properties=ent.get("properties", {}),
            entity_type=ent.get("type", "Unknown")
        )
        print(f"  ✓ {ent['name']}")
    
    # Run searches
    queries = [
        "rooms for meetings",
        "temperature monitoring",
        "building management",
        "who is in charge"
    ]
    
    print("\n" + "=" * 60)
    print("Search Results")
    print("=" * 60)
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        
        results = indexer.search(query, top_k=3, mode="hybrid")
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.metadata.get('name', result.id)}")
                print(f"     Score: {result.score:.3f}")
                print(f"     Type: {result.metadata.get('type', 'Unknown')}")
        else:
            print("  No results found")
    
    # Stats
    print("\n" + "=" * 60)
    print("Index Statistics")
    print("=" * 60)
    stats = indexer.get_index_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
