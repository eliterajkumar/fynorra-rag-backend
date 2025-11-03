"""LLM provider adapter supporting OpenRouter (default), Fynorra, OpenAI, Anthropic."""
import os
import requests
from typing import Dict, List
from src.config import Config
from src.security.crypto import decrypt_api_key


class LLMProvider:
    """Adapter for calling LLM APIs (Fynorra, OpenAI, Anthropic, etc.)."""
    
    def __init__(self, api_key: str = None, custom_api_key_encrypted: str = None, provider: str = "openrouter"):
        """
        Initialize LLM provider.
        
        Args:
            api_key: Default API key
            custom_api_key_encrypted: Encrypted user API key
            provider: LLM provider name (fynorra, openai, anthropic)
        """
        self.provider = provider
        
        if custom_api_key_encrypted:
            self.api_key = decrypt_api_key(custom_api_key_encrypted)
        else:
            # Choose default API key based on provider
            if provider == "openrouter":
                self.api_key = api_key or Config.OPENROUTER_API_KEY
            elif provider == "openai":
                self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
            elif provider == "anthropic":
                self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
            else:  # fynorra
                self.api_key = api_key or Config.FYNORRA_API_KEY
        
        # Set base URL based on provider
        if provider == "openrouter":
            self.base_url = Config.OPENROUTER_BASE_URL.rstrip("/")
        elif provider == "openai":
            self.base_url = "https://api.openai.com/v1"
        elif provider == "anthropic":
            self.base_url = "https://api.anthropic.com/v1"
        else:  # fynorra
            self.base_url = Config.FYNORRA_LLM_URL.replace("/chat/completions", "")
    
    def chat_completion(self, messages: List[Dict[str, str]], max_tokens: int = None, temperature: float = 0.7) -> str:
        """
        Generate chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
        
        Returns:
            Generated text response
        """
        max_tokens = max_tokens or Config.MAX_TOKENS
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self._get_model_name(),
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Anthropic uses different format
        if self.provider == "anthropic":
            headers["anthropic-version"] = "2023-06-01"
            payload = {
                "model": self._get_model_name(),
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract response based on provider
        if self.provider == "anthropic":
            return data["content"][0]["text"]
        else:
            return data["choices"][0]["message"]["content"]
    
    def _get_model_name(self) -> str:
        """Get model name based on provider."""
        if self.provider == "openrouter":
            # Use configured OpenRouter model (default in Config)
            return Config.OPENROUTER_MODEL
        elif self.provider == "openai":
            return "gpt-3.5-turbo"
        elif self.provider == "anthropic":
            return "claude-3-sonnet-20240229"
        else:  # fynorra
            return "fynorra-default"

