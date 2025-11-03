"""Pinecone vector database client wrapper with integrated embeddings support."""
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
from src.config import Config
import requests
import time
import random


class PineconeClient:
    """Wrapper for Pinecone vector operations with text-based integrated embeddings."""
    
    def __init__(self, api_key: str = None, env: str = None, index: str = None):
        """
        Initialize Pinecone client.
        
        Args:
            api_key: Pinecone API key (defaults to Config)
            env: Pinecone environment/region (defaults to Config)
            index: Index name (defaults to Config)
        """
        self.api_key = api_key or Config.PINECONE_API_KEY
        self.index_name = index or Config.PINECONE_INDEX
        self.env = env or Config.PINECONE_ENV or "us-east-1"
        
        # Initialize Pinecone SDK for control-plane operations
        self.pc = Pinecone(api_key=self.api_key)
        self.index = None
        self.base_url = None
        
        self._ensure_index()
        
        # Get data-plane URL from index host
        if self.index and hasattr(self.index, 'host'):
            self.base_url = f"https://{self.index.host}"
        else:
            # Fallback: try to construct URL (may need adjustment based on actual Pinecone setup)
            # For serverless, format is typically: {index-name}.{project-id}.svc.{environment}.pinecone.io
            # We'll use a simpler format that might need environment-specific configuration
            self.base_url = f"https://{self.index_name}.svc.pinecone.io"
    
    def _ensure_index(self):
        """Ensure the index exists, create if not."""
        # Check if index exists
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            # Create index with integrated embeddings (e5 model, typically 768 dimensions)
            # Note: When using integrated embeddings, dimension is set automatically
            self.pc.create_index(
                name=self.index_name,
                dimension=768,  # Default for e5 embeddings
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=self.env
                )
            )
        
        self.index = self.pc.Index(self.index_name)
    
    def _retry_with_backoff(self, func, max_retries: int = 3, initial_delay: float = 1.0):
        """
        Retry a function with exponential backoff and jitter.
        
        Args:
            func: Function to retry (should raise exception on failure)
            max_retries: Maximum number of retries
            initial_delay: Initial delay in seconds
        
        Returns:
            Function result
        """
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func()
            except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as e:
                last_exception = e
                if attempt < max_retries:
                    # Exponential backoff with jitter
                    jitter = random.uniform(0, 0.3 * delay)
                    time.sleep(delay + jitter)
                    delay *= 2
                else:
                    break
        
        raise last_exception
    
    def upsert_texts(self, namespace: str, records: List[dict], batch_size: int = None) -> dict:
        """
        Upsert text records to Pinecone using integrated embeddings (server-side).
        
        Args:
            namespace: Per-user namespace or global namespace
            records: List of dicts, each with {"id": str, "text": str, "metadata": dict}
            batch_size: Batch size for upserts (defaults to Config.BATCH_SIZE)
        
        Returns:
            dict: Summary { "batches_upserted": n, "records_upserted": m }
        
        Raises:
            Exception: On upsert failure after retries
        """
        if not records:
            return {"batches_upserted": 0, "records_upserted": 0}
        
        batch_size = batch_size or Config.BATCH_SIZE
        
        # Split into batches
        batches = [records[i:i + batch_size] for i in range(0, len(records), batch_size)]
        
        total_upserted = 0
        
        for batch in batches:
            # Prepare records for Pinecone API
            pinecone_records = []
            for rec in batch:
                pinecone_records.append({
                    "id": rec["id"],
                    "text": rec["text"],  # Pinecone will embed this server-side
                    "metadata": rec.get("metadata", {})
                })
            
            # Upsert via REST API (using records endpoint for text-based upserts)
            url = f"{self.base_url}/vectors/upsert"
            if namespace:
                url = f"{self.base_url}/namespaces/{namespace}/vectors/upsert"
            
            headers = {
                "Api-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Note: Pinecone API may use "records" or "vectors" depending on API version
            # Using "vectors" for compatibility, but may need "records" for text-based upserts
            payload = {"vectors": pinecone_records}
            
            def _upsert_batch():
                response = requests.post(url, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                return response.json()
            
            # Retry on 429/5xx
            result = self._retry_with_backoff(_upsert_batch)
            total_upserted += len(batch)
        
        return {
            "batches_upserted": len(batches),
            "records_upserted": total_upserted
        }
    
    def query_text(self, namespace: str, text: str, top_k: int = 8, include_metadata: bool = True, filter_dict: Dict = None) -> List[dict]:
        """
        Query Pinecone using text (server-side embedding).
        
        Args:
            namespace: Namespace to query
            text: Query text (will be embedded by Pinecone)
            top_k: Number of results
            include_metadata: Include metadata in results
            filter_dict: Metadata filters (e.g., {"user_id": "..."})
        
        Returns:
            List of results: [{"id": str, "score": float, "metadata": dict}, ...]
        """
        url = f"{self.base_url}/query"
        if namespace:
            url = f"{self.base_url}/namespaces/{namespace}/query"
        
        headers = {
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "topK": top_k,
            "includeMetadata": include_metadata,
            "text": text  # Pinecone will embed this server-side
        }
        
        if filter_dict:
            payload["filter"] = filter_dict
        
        def _query():
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        
        result = self._retry_with_backoff(_query)
        return result.get("matches", [])
    
    def upsert_vectors(self, vectors: List[Dict[str, Any]]):
        """
        Legacy method: Upsert pre-computed vectors to Pinecone.
        
        Args:
            vectors: List of dicts with 'id', 'values', and 'metadata'
        """
        if not vectors:
            return
        
        self.index.upsert(vectors=vectors)
    
    def query_vectors(self, query_vector: List[float], top_k: int = None, filter_dict: Dict = None) -> List[Dict]:
        """
        Legacy method: Query using pre-computed query vector.
        
        Args:
            query_vector: Embedding vector to search for
            top_k: Number of results (defaults to config)
            filter_dict: Metadata filters (e.g., {"user_id": "..."})
        
        Returns:
            List of matches with 'id', 'score', and 'metadata'
        """
        top_k = top_k or Config.TOP_K
        
        results = self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict
        )
        
        return results.get("matches", [])
    
    def delete_vectors(self, ids: List[str]):
        """Delete vectors by IDs."""
        if ids:
            self.index.delete(ids=ids)
    
    def delete_by_filter(self, filter_dict: Dict):
        """Delete vectors by metadata filter."""
        self.index.delete(filter=filter_dict)
    
    def create_index_for_model(self, index_name: str, model: str = "e5", dimension: int = 768, metric: str = "cosine") -> dict:
        """
        Optional control-plane wrapper to create index with hosted model.
        
        Args:
            index_name: Name of index to create
            model: Embedding model name (e.g., "e5")
            dimension: Vector dimension
            metric: Similarity metric
        
        Returns:
            dict: Creation result
        """
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        
        if index_name in existing_indexes:
            return {"status": "exists", "index": index_name}
        
        self.pc.create_index(
            name=index_name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(
                cloud="aws",
                region=self.env
            )
        )
        
        return {"status": "created", "index": index_name}

