"""
Pinecone client wrapper with OpenAI embeddings (default) and optional
commented-out open-source all-MiniLM-L6-v2 embedding code.

Usage:
    from src.embeddings.pinecone_client import PineconeClient
    pc = PineconeClient()
    pc.upsert_texts(namespace="user_123", records=[{"id":"doc1_chunk0","text":"hello world","metadata":{}}])
    res = pc.query_text(namespace="user_123", text="hello", top_k=5)
"""

import os
import time
import math
import logging
import random
from typing import List, Dict, Any, Optional, Callable

from pinecone import Pinecone
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Optional: uncomment to use local sentence-transformers (all-MiniLM-L6-v2)
# from sentence_transformers import SentenceTransformer

# Basic config via env or defaults
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_ENV = os.getenv("PINECONE_ENV", "")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "default-index")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "64"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")  # OpenAI embedding model
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "60"))

# Logging
logger = logging.getLogger("pinecone_client")
logging.basicConfig(level=logging.INFO)

# Init OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)


def _chunk_list(lst: List[Any], size: int) -> List[List[Any]]:
    return [lst[i : i + size] for i in range(0, len(lst), size)]


# Tenacity retry decorator for network calls (OpenAI/Pinecone)
network_retry = retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    retry=retry_if_exception_type(Exception),
)


class PineconeClient:
    def __init__(
        self,
        pinecone_api_key: Optional[str] = None,
        pinecone_env: Optional[str] = None,
        index_name: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
        batch_size: Optional[int] = None,
    ):
        """
        PineconeClient that computes embeddings using OpenAI (default) and upserts/queries Pinecone.

        Methods:
            upsert_texts(namespace, records): records = [{"id": str, "text": str, "metadata": dict}, ...]
            query_text(namespace, text, top_k)
            upsert_vectors(vectors)  # precomputed vectors
            query_vectors(query_vector, top_k)
        """
        self.pinecone_api_key = pinecone_api_key or PINECONE_API_KEY
        self.pinecone_env = pinecone_env or PINECONE_ENV
        self.index_name = index_name or PINECONE_INDEX
        self.embedding_model = embedding_model or EMBEDDING_MODEL
        self.batch_size = batch_size or BATCH_SIZE

        if not self.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY is required")

        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        # Ensure index exists (no-op if exists)
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        if self.index_name not in existing_indexes:
            logger.info("Creating Pinecone index '%s' with default dimension=1536 (adjust if needed)", self.index_name)
            # dimension depends on embedding model; text-embedding-3-small -> 1536
            # adjust dimension if using different model
            self.pc.create_index(
                name=self.index_name, 
                dimension=1536, 
                metric="cosine",
                spec={"serverless": {"cloud": "aws", "region": "us-east-1"}}
            )
        self.index = self.pc.Index(self.index_name)

        # Optional: initialize sentence-transformers locally (commented)
        # self.local_encoder = SentenceTransformer("all-MiniLM-L6-v2")  # uncomment to use local encoder

    # ---------------------
    # Embedding helpers
    # ---------------------
    @network_retry
    def _embed_texts_openai(self, texts: List[str]) -> List[List[float]]:
        """
        Batch embeddings via OpenAI. Retries on network errors.
        """
        # OpenAI allows batching; chunk accordingly
        embeddings: List[List[float]] = []
        # Guard: empty
        if not texts:
            return embeddings

        # Call OpenAI in batches to avoid giant requests
        text_batches = _chunk_list(texts, self.batch_size)
        for batch in text_batches:
            # Using the embeddings.create endpoint
            resp = openai_client.embeddings.create(model=self.embedding_model, input=batch, timeout=OPENAI_TIMEOUT)
            # resp['data'] is a list aligned with inputs
            batch_embeddings = [d["embedding"] for d in resp["data"]]
            embeddings.extend(batch_embeddings)
            # small sleep to be polite
            time.sleep(0.1)
        return embeddings

    # Optional open-source encoder (commented): use this if you want to run embeddings locally (no OpenAI)
    # def _embed_texts_local(self, texts: List[str]) -> List[List[float]]:
    #     """
    #     Local embedding using sentence-transformers all-MiniLM-L6-v2.
    #     Pros: free, deterministic. Cons: lower dimensionality (384), slower on CPU.
    #     """
    #     if not texts:
    #         return []
    #     # The local encoder returns numpy arrays; convert to lists
    #     vectors = self.local_encoder.encode(texts, show_progress_bar=False)
    #     return [v.tolist() for v in vectors]

    # ---------------------
    # Upsert helpers
    # ---------------------
    def upsert_texts(self, namespace: str, records: List[Dict[str, Any]], batch_size: Optional[int] = None) -> Dict[str, int]:
        """
        Upsert text records by computing OpenAI embeddings and upserting vectors to Pinecone.

        Args:
            namespace: Pinecone namespace (per-user or global)
            records: [{"id": str, "text": str, "metadata": dict}, ...]
            batch_size: override batch size for embedding/upsert (optional)
        Returns:
            {"batches_upserted": n, "records_upserted": m}
        """
        if not records:
            return {"batches_upserted": 0, "records_upserted": 0}

        batch_size = batch_size or self.batch_size

        # Split into batches to embed & upsert
        batches = _chunk_list(records, batch_size)
        total = 0
        for batch in batches:
            ids = [r["id"] for r in batch]
            texts = [r["text"] for r in batch]
            metas = [r.get("metadata", {}) for r in batch]

            # Compute embeddings (OpenAI)
            embeddings = self._embed_texts_openai(texts)

            # Prepare Pinecone vectors: {'id':..., 'values': [...], 'metadata': {...}}
            vectors = []
            for _id, vec, meta in zip(ids, embeddings, metas):
                vectors.append({"id": _id, "values": vec, "metadata": meta})

            # Upsert to Pinecone (with retries)
            self._upsert_with_retry(vectors=vectors, namespace=namespace)
            total += len(vectors)

        return {"batches_upserted": len(batches), "records_upserted": total}

    @network_retry
    def _upsert_with_retry(self, vectors: List[Dict[str, Any]], namespace: Optional[str] = None):
        """
        Upsert vectors to Pinecone index with retry wrapper.
        """
        if not self.index:
            raise ValueError("Pinecone index not initialized")
        if namespace:
            return self.index.upsert(vectors=vectors, namespace=namespace)
        return self.index.upsert(vectors=vectors)

    def upsert_vectors(self, vectors: List[Dict[str, Any]], namespace: Optional[str] = None):
        """
        Upsert pre-computed vectors directly.
        Each vector dict: {'id': str, 'values': List[float], 'metadata': dict}
        """
        if not vectors:
            return
        # chunk to avoid giant payloads
        for chunk in _chunk_list(vectors, self.batch_size):
            self._upsert_with_retry(vectors=chunk, namespace=namespace)

    # ---------------------
    # Query helpers
    # ---------------------
    def query_vectors(self, query_vector: List[float], top_k: int = 8, namespace: Optional[str] = None, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query Pinecone with a precomputed query vector.
        Returns list of matches (id, score, metadata).
        """
        if filter:
            res = self.index.query(vector=query_vector, top_k=top_k, include_values=False, include_metadata=True, namespace=namespace, filter=filter)
        else:
            res = self.index.query(vector=query_vector, top_k=top_k, include_values=False, include_metadata=True, namespace=namespace)
        return res.get("matches", [])

    def query_text(self, namespace: Optional[str], text: str, top_k: int = 8, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Compute embedding for `text` (via OpenAI) and query Pinecone.
        Returns Pinecone matches list with metadata.
        """
        # Embed query
        q_emb = self._embed_texts_openai([text])
        if not q_emb:
            return []
        return self.query_vectors(query_vector=q_emb[0], top_k=top_k, namespace=namespace, filter=filter)

    # ---------------------
    # Delete / management
    # ---------------------
    def delete_vectors(self, ids: List[str], namespace: Optional[str] = None):
        if not ids:
            return
        # Pinecone delete supports ids list
        if namespace:
            return self.index.delete(ids=ids, namespace=namespace)
        return self.index.delete(ids=ids)

    def delete_by_filter(self, filter: Dict[str, Any], namespace: Optional[str] = None):
        if not filter:
            return
        # Pinecone delete by filter
        if namespace:
            return self.index.delete(delete_filter=filter, namespace=namespace)
        return self.index.delete(delete_filter=filter)

    def create_index_for_model(self, index_name: str, dimension: int = 1536, metric: str = "cosine"):
        """
        Create an index if not exists. Default dimension 1536 (OpenAI text-embedding-3-small).
        Adjust dimension for different models.
        """
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        if index_name in existing_indexes:
            return {"status": "exists", "index": index_name}
        self.pc.create_index(
            name=index_name, 
            dimension=dimension, 
            metric=metric,
            spec={"serverless": {"cloud": "aws", "region": "us-east-1"}}
        )
        return {"status": "created", "index": index_name}
