"""Initial database migration - create all tables."""
from src.config import Config
from src.db.models import Base
from sqlalchemy import create_engine


def run_migration():
    """Create all database tables."""
    engine = create_engine(Config.DATABASE_URL)
    Base.metadata.create_all(engine)
    print("Migration completed: All tables created.")


if __name__ == "__main__":
    run_migration()

