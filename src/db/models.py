"""SQLAlchemy models for Fynorra RAG Backend."""
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


class User(Base):
    """User model (synced from Supabase Auth)."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    supabase_user_id = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    ingest_jobs = relationship("IngestJob", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    """Document model for uploaded/scraped content."""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # 'upload' or 'scrape'
    source_url = Column(String)  # URL or file path in Supabase Storage
    storage_path = Column(String)  # Path in Supabase Storage
    file_type = Column(String)  # 'pdf', 'html', 'txt', etc.
    metadata = Column(JSON)  # Additional metadata (page count, etc.)
    chunk_count = Column(Integer, default=0)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    ingest_jobs = relationship("IngestJob", back_populates="document")


class Chunk(Base):
    """Chunk model for text chunks with vector references."""
    __tablename__ = "chunks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    start_char = Column(Integer)
    end_char = Column(Integer)
    page_number = Column(Integer)  # For PDFs
    metadata = Column(JSON)  # Additional chunk metadata
    pinecone_id = Column(String)  # Pinecone vector ID
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")


class IngestJob(Base):
    """Ingestion job tracking model."""
    __tablename__ = "ingest_jobs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    job_type = Column(String, nullable=False)  # 'upload' or 'scrape'
    status = Column(String, default="queued")  # queued, processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text)
    celery_task_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="ingest_jobs")
    document = relationship("Document", back_populates="ingest_jobs")


class UserSettings(Base):
    """User settings including encrypted API keys."""
    __tablename__ = "user_settings"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    custom_llm_api_key_encrypted = Column(Text)  # Encrypted API key
    custom_embedding_api_key_encrypted = Column(Text)  # Encrypted embedding API key
    preferred_llm_provider = Column(String, default="fynorra")  # fynorra, openai, anthropic, etc.
    metadata = Column(JSON)  # Additional settings
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_models():
    """Initialize database tables."""
    from src.config import Config
    from sqlalchemy import create_engine
    
    engine = create_engine(Config.DATABASE_URL)
    Base.metadata.create_all(engine)

