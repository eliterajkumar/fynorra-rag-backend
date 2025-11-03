"""CLI commands for database migrations and admin tasks."""
import click
from src.config import Config
from src.db.session import get_db_session
from src.db.models import Base
from sqlalchemy import create_engine


@click.group()
def cli():
    """Fynorra RAG Backend CLI."""
    pass


@cli.command()
def init_db():
    """Initialize database tables."""
    from src.db.models import init_models
    init_models()
    click.echo("Database initialized.")


@cli.command()
def migrate():
    """Run database migrations."""
    # Placeholder for Alembic migrations
    click.echo("Migrations would run here (using Alembic in production).")


if __name__ == "__main__":
    cli()

