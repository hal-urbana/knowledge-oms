"""
LightRAG Indexer - Semantic Search Integration
Provides intelligent search and retrieval capabilities over knowledge graph entities
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Represents a document/chunk for indexing."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Represents a search result from the index."""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class LightRAGIndexer:
    """
    Simple LightRAG-like semantic indexer for Knowledge OMS.
    
    Provides:
    - Document chunking and embedding generation
    - Vector storage for semantic search
    - Hybrid keyword + semantic search
    - Entity indexing from knowledge graphs
    
    Note: This is a simplified implementation. For production use,
    consider the full LightRAG library from https://github.comYOURORG/LightRAG
    """
    
    def __init__(
        self,
        persist_dir: str = "./lightrag_data",
        embedding_model: str = "text-embedding-ada-002",
        embedding_dim: int = 1536
    ):
        """
        Initialize the LightRAG indexer.
        
        Args:
            persist_dir: Directory for persisting index data
            embedding_model: Name of embedding model to use
            embedding_dim: Dimension of embedding vectors
        """
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
        
        # In-memory storage (would be vector DB in production)
        self._documents: Dict[str, Document] = {}
        self._embeddings: Dict[str, List[float]] = {}
        self._index_built = False
        
        os.makedirs(persist_dir, exist_ok=True)
        self._load_index()
    
    def _load_index(self) -> None:
        """Load existing index from disk if available."""
        index_file = os.path.join(self.persist_dir, "index.json")
        embeddings_file = os.path.join(self.persist_dir, "embeddings.json")
        
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r') as f:
                    data = json.load(f)
                    for doc in data.get('documents', []):
                        self._documents[doc['id']] = Document(**doc)
                logger.info(f"Loaded {len(self._documents)} documents from index")
            except Exception as e:
                logger.warning(f"Failed to load index: {e}")
        
        if os.path.exists(embeddings_file):
            try:
                with open(embeddings_file, 'r') as f:
                    self._embeddings = json.load(f)
                logger.info(f"Loaded {len(self._embeddings)} embeddings")
            except Exception as e:
                logger.warning(f"Failed to load embeddings: {e}")
    
    def _save_index(self) -> None:
        """Persist index to disk."""
        index_file = os.path.join(self.persist_dir, "index.json")
        embeddings_file = os.path.join(self.persist_dir, "embeddings.json")
        
        docs_data = [doc.__dict__ for doc in self._documents.values()]
        
        with open(index_file, 'w') as f:
            json.dump({'documents': docs_data, 'count': len(docs_data)}, f)
        
        with open(embeddings_file, 'w') as f:
            json.dump(self._embeddings, f)
        
        logger.info(f"Saved index with {len(self._documents)} documents")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        In production, this would call an embedding API.
        For now, uses a simple hash-based placeholder.
        """
        # Simple deterministic embedding based on text hash
        # In production, use OpenAI/Cohere/etc embeddings
        import hashlib
        import numpy as np
        
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        np.random.seed(hash_val % (2**32))
        embedding = np.random.randn(self.embedding_dim).astype(np.float32)
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding.tolist()
    
    def _compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Compute cosine similarity between two embeddings."""
        import numpy as np
        
        e1 = np.array(embedding1)
        e2 = np.array(embedding2)
        
        dot = np.dot(e1, e2)
        norm1 = np.linalg.norm(e1)
        norm2 = np.linalg.norm(e2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot / (norm1 * norm2))
    
    def index_entity(
        self,
        entity_id: str,
        name: str,
        description: str,
        properties: Optional[Dict[str, Any]] = None,
        entity_type: str = "Unknown"
    ) -> None:
        """
        Index a knowledge graph entity for search.
        
        Args:
            entity_id: Unique identifier for the entity
            name: Entity name/title
            description: Text description for searching
            properties: Additional properties
            entity_type: Type of entity
        """
        content = self._prepare_content(name, description, properties, entity_type)
        
        doc = Document(
            id=entity_id,
            content=content,
            metadata={
                'name': name,
                'type': entity_type,
                'properties': properties or {},
                'indexed_at': datetime.now().isoformat()
            }
        )
        
        self._documents[entity_id] = doc
        self._embeddings[entity_id] = self._generate_embedding(content)
        self._index_built = False
    
    def index_documents(self, documents: List[Document]) -> None:
        """
        Index multiple documents at once.
        
        Args:
            documents: List of Document objects
        """
        for doc in documents:
            self._documents[doc.id] = doc
            self._embeddings[doc.id] = self._generate_embedding(doc.content)
        
        self._index_built = False
        logger.info(f"Indexed {len(documents)} documents")
    
    def _prepare_content(
        self,
        name: str,
        description: str,
        properties: Optional[Dict[str, Any]],
        entity_type: str
    ) -> str:
        """Prepare searchable text content from entity data."""
        parts = [name, entity_type, description]
        
        if properties:
            for key, value in properties.items():
                if isinstance(value, str):
                    parts.append(value)
                elif isinstance(value, (int, float, bool)):
                    parts.append(str(value))
        
        return " | ".join(filter(None, parts))
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        mode: str = "semantic"
    ) -> List[SearchResult]:
        """
        Search indexed entities.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            mode: Search mode - "semantic", "keyword", or "hybrid"
            
        Returns:
            List of SearchResult objects ranked by relevance
        """
        if not self._documents:
            return []
        
        query_embedding = self._generate_embedding(query)
        scores: Dict[str, float] = {}
        
        for doc_id, embedding in self._embeddings.items():
            if doc_id not in self._documents:
                continue
            
            if mode == "semantic":
                score = self._compute_similarity(query_embedding, embedding)
            elif mode == "keyword":
                score = self._keyword_score(query, self._documents[doc_id].content)
            else:  # hybrid
                sem_score = self._compute_similarity(query_embedding, embedding)
                key_score = self._keyword_score(query, self._documents[doc_id].content)
                score = 0.5 * sem_score + 0.5 * key_score
            
            scores[doc_id] = score
        
        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in ranked[:top_k]:
            if score > 0:
                doc = self._documents[doc_id]
                results.append(SearchResult(
                    id=doc.id,
                    content=doc.content,
                    score=score,
                    metadata=doc.metadata
                ))
        
        return results
    
    def _keyword_score(self, query: str, content: str) -> float:
        """Simple keyword matching score."""
        query_terms = set(query.lower().split())
        content_lower = content.lower()
        
        if not query_terms:
            return 0.0
        
        matches = sum(1 for term in query_terms if term in content_lower)
        return matches / len(query_terms)
    
    def delete_entity(self, entity_id: str) -> None:
        """Remove an entity from the index."""
        self._documents.pop(entity_id, None)
        self._embeddings.pop(entity_id, None)
        self._index_built = False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the current index."""
        return {
            'document_count': len(self._documents),
            'embedding_dim': self.embedding_dim,
            'persist_dir': self.persist_dir,
            'models': {
                'embedding': self.embedding_model
            }
        }


def create_indexer_from_env() -> LightRAGIndexer:
    """
    Factory to create LightRAGIndexer from environment variables.
    """
    return LightRAGIndexer(
        persist_dir=os.getenv("LIGHTRAG_PERSIST_DIR", "./lightrag_data"),
        embedding_model=os.getenv("LIGHTRAG_EMBEDDING_MODEL", "text-embedding-ada-002"),
        embedding_dim=int(os.getenv("LIGHTRAG_EMBEDDING_DIM", "1536"))
    )
