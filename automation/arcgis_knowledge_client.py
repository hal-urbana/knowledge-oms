"""
ArcGIS Knowledge API Client for Knowledge OMS
Python client for interacting with ArcGIS Knowledge REST API
Supports entity and relationship management in knowledge graphs
"""

import os
import requests
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Represents a knowledge graph entity with geographic properties"""
    name: str
    type_name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    entity_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "typeName": self.type_name,
            "properties": self.properties
        }


@dataclass
class Relationship:
    """Represents a relationship between entities"""
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    relationship_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sourceEntityId": self.source_entity_id,
            "targetEntityId": self.target_entity_id,
            "relationshipType": self.relationship_type,
            "properties": self.properties
        }


class ArcGISKnowledgeClient:
    """
    Client for ArcGIS Knowledge Server REST API.
    
    Handles authentication via OAuth2 with ArcGIS Enterprise Portal,
    and provides methods for CRUD operations on entities and relationships
    within knowledge graphs.
    """
    
    def __init__(
        self,
        portal_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True
    ):
        """
        Initialize the ArcGIS Knowledge client.
        
        Args:
            portal_url: Full URL of ArcGIS Enterprise portal (e.g., https://server.arcgis.com)
            username: Portal username
            password: Portal password
            verify_ssl: Whether to verify SSL certificates
        """
        self.portal_url = portal_url.rstrip('/')
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _get_token(self) -> str:
        """Authenticate with portal and get access token."""
        if self._token and self._token_expiry:
            if datetime.now() < self._token_expiry:
                return self._token
        
        token_url = f"{self.portal_url}/sharing/rest/token"
        params = {
            "username": self.username,
            "password": self.password,
            "client": "referer",
            "referer": self.portal_url,
            "expiration": 60,
            "f": "json"
        }
        
        response = requests.get(
            token_url, 
            params=params, 
            verify=self.verify_ssl,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if "token" not in data:
            raise ValueError(f"Authentication failed: {data}")
        
        self._token = data["token"]
        self._token_expiry = datetime.now()
        logger.info("Successfully authenticated with ArcGIS portal")
        return self._token
    
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Make authenticated request to ArcGIS REST API."""
        url = f"{self.portal_url}/sharing/rest{endpoint}"
        params = kwargs.get("params", {})
        params["token"] = self._get_token()
        params["f"] = "json"
        kwargs["params"] = params
        
        if "timeout" not in kwargs:
            kwargs["timeout"] = 30
        
        response = requests.request(
            method, 
            url, 
            verify=self.verify_ssl,
            **kwargs
        )
        response.raise_for_status()
        return response.json()
    
    # -------------------------------------------------------------------------
    # Knowledge Graph Operations
    # -------------------------------------------------------------------------
    
    def get_knowledge_graph(self, kg_id: str) -> Dict[str, Any]:
        """Get knowledge graph metadata."""
        return self._request("GET", f"/knowledgeBases/{kg_id}")
    
    def list_knowledge_graphs(self) -> List[Dict[str, Any]]:
        """List all accessible knowledge graphs."""
        data = self._request("GET", "/knowledgeBases")
        return data.get("knowledgeBases", [])
    
    def create_knowledge_graph(
        self,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new knowledge graph.
        
        Args:
            title: Title for the knowledge graph
            description: Optional description
            tags: Optional list of tags
            
        Returns:
            Dict containing the created knowledge graph info
        """
        params = {
            "title": title,
            "description": description
        }
        if tags:
            params["tags"] = ",".join(tags)
        
        return self._request("POST", "/knowledgeBases/create", json=params)
    
    # -------------------------------------------------------------------------
    # Entity Operations
    # -------------------------------------------------------------------------
    
    def create_entity(
        self,
        kg_id: str,
        entity: Entity
    ) -> Entity:
        """
        Create a new entity in a knowledge graph.
        
        Args:
            kg_id: Knowledge graph ID
            entity: Entity object to create
            
        Returns:
            Entity with updated entity_id
        """
        endpoint = f"/knowledgeBases/{kg_id}/entities/add"
        
        payload = {
            "entities": [entity.to_dict()]
        }
        
        result = self._request("POST", endpoint, json=payload)
        
        if result.get("entities"):
            entity.entity_id = result["entities"][0].get("id")
            logger.info(f"Created entity: {entity.name} ({entity.entity_id})")
            return entity
        
        raise ValueError(f"Failed to create entity: {result}")
    
    def get_entity(
        self,
        kg_id: str,
        entity_id: str
    ) -> Dict[str, Any]:
        """Retrieve an entity by ID."""
        return self._request("GET", f"/knowledgeBases/{kg_id}/entities/{entity_id}")
    
    def search_entities(
        self,
        kg_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for entities using a text query.
        
        Args:
            kg_id: Knowledge graph ID
            query: Search text
            limit: Maximum results
            
        Returns:
            List of matching entities
        """
        params = {
            "searchText": query,
            "limit": limit
        }
        data = self._request("GET", f"/knowledgeBases/{kg_id}/entities/search", params=params)
        return data.get("results", [])
    
    def update_entity(
        self,
        kg_id: str,
        entity_id: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an entity's properties."""
        endpoint = f"/knowledgeBases/{kg_id}/entities/{entity_id}/update"
        return self._request("POST", endpoint, json={"properties": properties})
    
    def delete_entity(
        self,
        kg_id: str,
        entity_id: str
    ) -> Dict[str, Any]:
        """Delete an entity from the knowledge graph."""
        endpoint = f"/knowledgeBases/{kg_id}/entities/{entity_id}/delete"
        return self._request("POST", endpoint)
    
    def create_entities_batch(
        self,
        kg_id: str,
        entities: List[Entity]
    ) -> List[Entity]:
        """
        Create multiple entities in a batch operation.
        
        Args:
            kg_id: Knowledge graph ID
            entities: List of Entity objects
            
        Returns:
            List of entities with updated IDs
        """
        endpoint = f"/knowledgeBases/{kg_id}/entities/add"
        
        payload = {
            "entities": [e.to_dict() for e in entities]
        }
        
        result = self._request("POST", endpoint, json=payload)
        
        if result.get("entities"):
            for i, ent_data in enumerate(result["entities"]):
                if i < len(entities):
                    entities[i].entity_id = ent_data.get("id")
        
        logger.info(f"Batch created {len(entities)} entities")
        return entities
    
    # -------------------------------------------------------------------------
    # Relationship Operations
    # -------------------------------------------------------------------------
    
    def create_relationship(
        self,
        kg_id: str,
        relationship: Relationship
    ) -> Relationship:
        """
        Create a new relationship between entities.
        
        Args:
            kg_id: Knowledge graph ID
            relationship: Relationship object
            
        Returns:
            Relationship with updated ID
        """
        endpoint = f"/knowledgeBases/{kg_id}/relationships/add"
        
        payload = {
            "relationships": [relationship.to_dict()]
        }
        
        result = self._request("POST", endpoint, json=payload)
        
        if result.get("relationships"):
            relationship.relationship_id = result["relationships"][0].get("id")
            logger.info(f"Created relationship: {relationship.relationship_type}")
            return relationship
        
        raise ValueError(f"Failed to create relationship: {result}")
    
    def get_relationships_for_entity(
        self,
        kg_id: str,
        entity_id: str
    ) -> List[Dict[str, Any]]:
        """Get all relationships for a specific entity."""
        return self._request("GET", f"/knowledgeBases/{kg_id}/entities/{entity_id}/relationships")
    
    def delete_relationship(
        self,
        kg_id: str,
        relationship_id: str
    ) -> Dict[str, Any]:
        """Delete a relationship."""
        endpoint = f"/knowledgeBases/{kg_id}/relationships/{relationship_id}/delete"
        return self._request("POST", endpoint)
    
    # -------------------------------------------------------------------------
    # Data Import / Export
    # -------------------------------------------------------------------------
    
    def import_data(
        self,
        kg_id: str,
        file_path: str,
        format_type: str = "geojson"
    ) -> Dict[str, Any]:
        """
        Import data from a file into the knowledge graph.
        
        Args:
            kg_id: Knowledge graph ID
            file_path: Path to data file
            format_type: Format of data (geojson, csv, etc.)
        """
        with open(file_path, 'rb') as f:
            files = {'file': f}
            return self._request("POST", f"/knowledgeBases/{kg_id}/import", files=files)
    
    def export_data(
        self,
        kg_id: str,
        format_type: str = "json"
    ) -> Dict[str, Any]:
        """Export knowledge graph data."""
        params = {"format": format_type}
        return self._request("GET", f"/knowledgeBases/{kg_id}/export", params=params)


def create_client_from_env() -> ArcGISKnowledgeClient:
    """
    Factory function to create client from environment variables.
    
    Reads ARCGIS_PORTAL_URL, ARCGIS_USERNAME, ARCGIS_PASSWORD,
    and ARCGIS_VERIFY_SSL from environment.
    """
    return ArcGISKnowledgeClient(
        portal_url=os.getenv("ARCGIS_PORTAL_URL", ""),
        username=os.getenv("ARCGIS_USERNAME", ""),
        password=os.getenv("ARCGIS_PASSWORD", ""),
        verify_ssl=os.getenv("ARCGIS_VERIFY_SSL", "true").lower() == "true"
    )
