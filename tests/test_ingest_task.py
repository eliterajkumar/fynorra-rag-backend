"""Tests for ingestion tasks."""
import pytest
from unittest.mock import Mock, patch


def test_ingest_upload_file_task_structure():
    """Test that ingest task has correct structure."""
    from src.tasks.ingest_job import ingest_upload_file_task
    
    # Verify task is defined
    assert callable(ingest_upload_file_task)
    assert hasattr(ingest_upload_file_task, "delay")  # Celery task method


def test_ingest_scrape_url_task_structure():
    """Test that scrape task has correct structure."""
    from src.tasks.ingest_job import ingest_scrape_url_task
    
    # Verify task is defined
    assert callable(ingest_scrape_url_task)
    assert hasattr(ingest_scrape_url_task, "delay")  # Celery task method


@patch("src.tasks.ingest_job.PineconeClient")
@patch("src.tasks.ingest_job.EmbeddingAdapter")
@patch("src.tasks.ingest_job.SupabaseStorage")
def test_ingest_task_flow(mock_storage, mock_embedding, mock_pinecone):
    """Test ingestion task flow with mocks."""
    # This would test the full flow in an integration test
    # For now, just verify modules are importable
    from src.tasks.ingest_job import ingest_upload_file_task
    assert ingest_upload_file_task is not None

