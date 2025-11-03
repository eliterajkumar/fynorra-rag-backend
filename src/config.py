"""Configuration management for Fynorra RAG Backend."""
import os
from typing import Optional
from pathlib import Path


class Config:
    """Application configuration loaded from environment variables."""
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Redis & Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Pinecone
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENV: str = os.getenv("PINECONE_ENV", "")
    PINECONE_INDEX: str = os.getenv("PINECONE_INDEX", "fynorra-dev-1")
    
    # Fynorra
    FYNORRA_API_KEY: str = os.getenv("FYNORRA_API_KEY", "")
    FYNORRA_EMBEDDING_URL: str = os.getenv("FYNORRA_EMBEDDING_URL", "https://api.fynorra.com/v1/embeddings")
    FYNORRA_LLM_URL: str = os.getenv("FYNORRA_LLM_URL", "https://api.fynorra.com/v1/chat/completions")
    
    # OpenRouter (default LLM)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b")
    
    # Security
    MASTER_KEY: str = os.getenv("MASTER_KEY", "")
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    
    # Environment
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = ENV == "development"
    
    # Flask
    SECRET_KEY: str = os.getenv("SECRET_KEY", os.urandom(24).hex())
    
    # RAG Settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    TOP_K: int = int(os.getenv("TOP_K", "5"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "500"))
    
    # Upload & Processing
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", "20971520"))  # 20MB
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "64"))  # Pinecone upsert batch size
    
    # Storage
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "fynorra-documents")
    # Optional S3-compatible access for Supabase Storage
    SUPABASE_S3_ENABLED: bool = os.getenv("SUPABASE_S3_ENABLED", "false").lower() == "true"
    SUPABASE_S3_ENDPOINT: str = os.getenv("SUPABASE_S3_ENDPOINT", "")
    SUPABASE_S3_REGION: str = os.getenv("SUPABASE_S3_REGION", "")
    SUPABASE_S3_ACCESS_KEY_ID: str = os.getenv("SUPABASE_S3_ACCESS_KEY_ID", "")
    SUPABASE_S3_SECRET_ACCESS_KEY: str = os.getenv("SUPABASE_S3_SECRET_ACCESS_KEY", "")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required config values are set."""
        required = [
            "SUPABASE_URL",
            "SUPABASE_SERVICE_KEY",
            "DATABASE_URL",
            "PINECONE_API_KEY",
            "MASTER_KEY",
        ]
        # At least one LLM default key should be present; prefer OpenRouter
        if not cls.OPENROUTER_API_KEY and not cls.FYNORRA_API_KEY:
            raise ValueError("Missing required config: OPENROUTER_API_KEY (or FYNORRA_API_KEY)")
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")
        return True

