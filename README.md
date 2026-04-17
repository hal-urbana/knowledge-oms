# Knowledge OMS (Object Management System)

**Project:** Knowledge OMS - Esri Knowledge Server + LightRAG integration for ArcGIS Pro mapping with Unified Data Library (UDL) message broker.

**Repository:** http://192.168.10.42/hal/knowledge-oms

**Status:** Active Development

---

## Project Overview

Knowledge OMS is a knowledge base system built on **Esri ArcGIS Knowledge Server** (via ArcGIS Portal) that interfaces with external data sources, specifically the **Unified Data Library (UDL)** — a Kafka-based message broker — and displays geographic content over maps in **ArcGIS Pro**.

The system integrates **LightRAG** (an open-source RAG framework) to provide intelligent search and retrieval capabilities across knowledge graph objects.

### Key Goals

- **ArcGIS Knowledge (2025/2026 update):** Enhanced support for registering NoSQL data stores and cloud-native graph databases (Net4j). ArcGIS 12.0 includes improved migration and cross-portal sharing for knowledge graphs.
- **LightRAG Methodology:** Implements a dual-level retrieval paradigm (chunk-level and relationship-level) to provide contextually rich answers by understanding the complex inter-dependencies between primary and associated objects.
- **UDL Integration:** The OMS uses Kafka as the primary ingestion backbone, mapping Space Force UDL schemas directly into Esri Knowledge Graph entities and relationships.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Unified Data Library (UDL)                    │
│                    (Kafka Message Broker)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ (Kafka messages)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      UDL Adapter                                │
│                 (Kafka Consumer Layer)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LightRAG Engine                              │
│               (Open-source RAG Framework)                      │
│               (Knowledge Index + Semantic Search)                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               ArcGIS Knowledge Client                           │
│           (Esri Knowledge Server REST API)                      │
│           (Entities + Relationships + Geometry)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ArcGIS Knowledge Server                        │
│                   (On Portal)                                   │
│           (Geographic entities & relationships)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ArcGIS Pro                                 │
│                   (Map Visualization)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. UDL Adapter (`automation/udl_adapter.py`)
- Kafka-based message broker adapter for UDL
- Topic subscriptions for data ingestion
- Authentication and TLS support
- Message parsing and validation
- Batch consumption for high throughput

### 2. LightRAG Indexer (`automation/lightrag_indexer.py`)
- Open-source RAG framework integration
- Document chunking and embedding generation
- Vector storage for semantic search
- Hybrid keyword + semantic search
- Entity indexing from knowledge graphs

### 3. ArcGIS Knowledge Client (`automation/arcgis_knowledge_client.py`)
- Full API client for ArcGIS Knowledge REST API
- Authentication via OAuth2 with ArcGIS Enterprise
- CRUD operations for entities and relationships
- Batch operations with async support
- Geometry/geographic property support

### 4. Ingest Service (`automation/ingest_service.py`)
- Core orchestration layer
- Coordinates UDL consumption → Transform → ArcGIS + LightRAG
- Supports **Object Management System (OMS)** relationships
- Automatically links primary UDL objects to associated information objects
- Batch processing and retry logic

---

## OMS Features (Object Management System)

The Knowledge OMS implementation specifically addresses the requirement to display primary objects from UDL along with associated information:

1. **Primary Object Mapping**: Geographic properties (geometry/Shape) from UDL are preserved and ingested into ArcGIS Knowledge entities for display in ArcGIS Pro.
2. **Automated Linking**: When a UDL message contains `associated_objects`, the system automatically:
   - Creates the primary entity.
   - Creates each associated information object as a related entity.
   - Establishes `ASSOCIATED_WITH` (or specific sub-type) relationships in the knowledge graph.
3. **Semantic Enrichment**: The LightRAG indexer captures both primary and associated objects, allowing for semantic queries that can cross-reference intelligence against geographic targets.

---

## Technology Stack

| Component | Technology |
|---|---|
| Knowledge Server | Esri ArcGIS Knowledge Server (on Portal) |
| Message Broker | Unified Data Library (UDL) - Kafka |
| RAG Framework | LightRAG (open-source) |
| Map Client | ArcGIS Pro |
| API | ArcGIS Knowledge REST API |
| Authentication | OAuth2 / ArcGIS Enterprise |

---

## Directory Structure

```
knowledge-oms/
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
│
├── automation/                      # Core automation modules
│   ├── __init__.py
│   ├── arcgis_knowledge_client.py   # ArcGIS Knowledge API client
│   ├── udl_adapter.py               # UDL/Kafka consumer adapter
│   ├── lightrag_indexer.py          # LightRAG semantic indexer
│   └── ingest_service.py            # Main ingest orchestration
│
├── examples/                        # Usage examples
│   ├── __init__.py
│   ├── create_knowledge_graph.py    # Create KG with entities
│   └── query_lightrag.py            # Semantic search example
│
└── tests/                           # Unit tests
```

---

## Getting Started

### Prerequisites

- ArcGIS Enterprise 10.9+ with ArcGIS Knowledge Server
- Access to Unified Data Library (UDL) Kafka broker
- Python 3.9+
- ArcGIS Pro (for map visualization)

### Installation

```bash
# Clone the repository
git clone http://192.168.10.42/hal/knowledge-oms.git
cd knowledge-oms

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials:
# - ARCGIS_PORTAL_URL: ArcGIS Enterprise portal URL
# - ARCGIS_USERNAME: Portal username
# - ARCGIS_PASSWORD: Portal password
# - UDL_BOOTSTRAP_SERVERS: UDL Kafka broker endpoints
# - UDL_TOPIC: Topic to subscribe to
```

### Basic Usage

```python
from automation.arcgis_knowledge_client import ArcGISKnowledgeClient
from automation.lightrag_indexer import LightRAGIndexer

# Initialize clients
kg_client = ArcGISKnowledgeClient(
    portal_url="https://your-portal.arcgis.com",
    username="your-username",
    password="your-password"
)

rag_indexer = LightRAGIndexer(
    persist_dir="./lightrag_data",
    embedding_dim=1536
)

# Search knowledge base
results = rag_indexer.search(
    query="Show facilities with geographic coordinates",
    top_k=10,
    mode="hybrid"
)
```

### Run Examples

```bash
# Run the OMS Object Management System demo
python -m examples.udl_oms_demo

# Create a knowledge graph with sample entities
python -m examples.create_knowledge_graph
```

---

## Data Flow

1. **UDL → Kafka Consumer:** Subscribe to UDL topics for incoming messages
2. **Message Parsing:** Parse UDL message format (JSON-based)
3. **Validation:** Validate schema and data integrity
4. **Transformation:** Map UDL payload to Knowledge entity format
5. **LightRAG Indexing:** Index document content for semantic search
6. **ArcGIS Knowledge:** Create entities and relationships
7. **ArcGIS Pro:** Visualize geographic objects on map

---

## Related Repositories

| Repository | Purpose |
|---|---|
| `arcgis-knowledge-integration` | Python API client for ArcGIS Knowledge |
| `esri-knowledge-ul` | UDL integration with Esri Knowledge |
| `esri-knowledge-lightrag-research` | Research on Esri Knowledge + LightRAG |
| `esri-knowledge-lightrag-integration` | Integration implementation |

---

## References

### Documentation
- [ArcGIS Knowledge Documentation](https://enterprise.arcgis.com/en/knowledge/latest/manage/manage-arcgis-knowledge.htm)
- [Esri Knowledge Studio Guide](https://enterprise.arcgis.com/en/knowledge/latest/knowledge/getting-started-with-knowledge-studio.htm)
- [LightRAG Research Summary](RESEARCH_SUMMARY.md) - Comprehensive research findings

### Source Code
- [LightRAG GitHub](https://github.com/HKUDS/LightRAG)
- [LightRAG Research Paper](https://arxiv.org/abs/2410.05779)

### Data Sources
- [Unified Data Library Overview](https://www.ssc.spaceforce.mil/Portals/3/SDA%20Briefings/06.%20UDL%20Overview%20Overview.pdf)
- [Space Force UDL Strategy](https://breakingdefense.com/2025/03/space-force-unveils-multi-front-push-to-fix-its-unified-data-library/)

---

## Status History

| Date | Status | Notes |
|---|---|---|
| 2026-02-26 | Design | Initial architecture and pipeline design |
| 2026-03-20 | Active | Development in progress |
| 2026-03-30 | Active | Implementation complete - README updated |

---

## Contact

**Project Owner:** Hal (hal@usmlabs.com)

**Slack:** #all-usmlabs

---

*Last updated: 2026-03-30*
