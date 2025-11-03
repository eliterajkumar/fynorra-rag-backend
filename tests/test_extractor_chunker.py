"""Tests for text extraction and chunking."""
import pytest
from src.ingest.extractor import extract_text_from_html, extract_text_from_file
from src.ingest.chunker import TextChunker


def test_extract_text_from_html():
    """Test HTML text extraction."""
    html = "<html><body><h1>Title</h1><p>Paragraph text here.</p></body></html>"
    text = extract_text_from_html(html)
    assert "Title" in text
    assert "Paragraph text here" in text


def test_text_chunker():
    """Test text chunking."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    text = "This is a test document. " * 20  # Long text
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) > 0
    assert all("content" in chunk for chunk in chunks)
    assert all("start_char" in chunk for chunk in chunks)
    assert all("end_char" in chunk for chunk in chunks)


def test_chunker_overlap():
    """Test that chunks have proper overlap."""
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    text = "word " * 100  # 100 words
    chunks = chunker.chunk_text(text)
    
    # Check overlap between consecutive chunks
    if len(chunks) > 1:
        first_end = chunks[0]["end_char"]
        second_start = chunks[1]["start_char"]
        # Second chunk should start before first ends (overlap)
        assert second_start < first_end

