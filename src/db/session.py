"""Database session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from src.config import Config

engine = create_engine(Config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def get_db_session():
    """Get a database session."""
    return SessionLocal()


def init_db():
    """Initialize database connection."""
    from src.db.models import init_models
    init_models()

