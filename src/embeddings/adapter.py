"""Embedding provider adapter for Fynorra and other APIs."""
import requests
from typing import List, Optional
from src.config import Config
from src.security.crypto import decrypt_api_key


class EmbeddingAdapter:
    """Adapter for generating embeddings from various providers."""
    
    def __init__(self, api_key: 'Optional[str]' = None, custom_api_key_encrypted: 'Optional[str]' = None):
        """
        Initialize embedding adapter.
        
        Args:
            api_key: Fynorra API key (default)
            custom_api_key_encrypted: Encrypted custom API key for user
        """
        if custom_api_key_encrypted:
            self.api_key = decrypt_api_key(custom_api_key_encrypted)
            self.base_url = "https://api.openai.com/v1"  # Default to OpenAI format
        else:
            self.api_key = api_key or Config.FYNORRA_API_KEY
            self.base_url = Config.FYNORRA_EMBEDDING_URL.replace("/embeddings", "")
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = self.embed_texts([text])
        return embeddings[0] if embeddings else []
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        # Use Fynorra endpoint format
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Prepare request
        payload = {
            "input": texts,
            "model": "text-embedding-ada-002"  # Default model, can be configurable
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        embeddings = [item["embedding"] for item in data.get("data", [])]
        
        return embeddings

