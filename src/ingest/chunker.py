"""Text chunking utilities for RAG."""
from typing import List
from src.config import Config


class TextChunker:
    """Chunk text into smaller pieces for embedding."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or Config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or Config.CHUNK_OVERLAP
    
    def chunk_text(self, text: str, metadata: dict = None) -> List[dict]:
        """
        Split text into chunks with overlap.
        
        Returns:
            List of dicts with 'content', 'start_char', 'end_char', and metadata
        """
        if not text:
            return []
        
        chunks = []
        text_length = len(text)
        start = 0
        
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunk_text = text[start:end]
            
            # Try to break at sentence boundary if not at end
            if end < text_length:
                # Look for sentence endings
                for break_char in [".\n", ".\n\n", ".\n ", "\n\n", "\n"]:
                    last_break = chunk_text.rfind(break_char)
                    if last_break > self.chunk_size * 0.5:  # Don't break too early
                        chunk_text = text[start:start + last_break + 1]
                        end = start + last_break + 1
                        break
            
            chunk_data = {
                "content": chunk_text.strip(),
                "start_char": start,
                "end_char": end,
                **metadata if metadata else {}
            }
            chunks.append(chunk_data)
            
            # Move start position with overlap
            start = end - self.chunk_overlap if end < text_length else end
        
        return chunks
    
    def chunk_pages(self, pages: List[str], max_chars: int = None, overlap: int = None) -> List[dict]:
        """
        Chunk a list of pages, preserving page information.
        
        Args:
            pages: List of strings (one per page or section)
            max_chars: Maximum characters per chunk (defaults to chunk_size)
            overlap: Character overlap between chunks (defaults to chunk_overlap)
        
        Returns:
            List of chunk dicts with 'text', 'page', 'chunk_index', 'start_char', 'end_char', 'preview'
        """
        max_chars = max_chars or self.chunk_size
        overlap = overlap or self.chunk_overlap
        
        chunks = []
        global_chunk_idx = 0
        
        for page_idx, page_text in enumerate(pages):
            if not page_text.strip():
                continue
            
            # Chunk this page
            page_length = len(page_text)
            start = 0
            
            while start < page_length:
                end = min(start + max_chars, page_length)
                chunk_text = page_text[start:end]
                
                # Try to break at sentence boundary if not at end
                if end < page_length:
                    for break_char in [".\n", ".\n\n", ".\n ", "\n\n", "\n"]:
                        last_break = chunk_text.rfind(break_char)
                        if last_break > max_chars * 0.5:  # Don't break too early
                            chunk_text = page_text[start:start + last_break + 1]
                            end = start + last_break + 1
                            break
                
                chunk_data = {
                    "text": chunk_text.strip(),
                    "page": page_idx + 1,  # 1-indexed page number
                    "chunk_index": global_chunk_idx,
                    "start_char": start,
                    "end_char": end,
                    "preview": chunk_text.strip()[:200]  # Preview for metadata
                }
                chunks.append(chunk_data)
                global_chunk_idx += 1
                
                # Move start position with overlap
                start = end - overlap if end < page_length else end
        
        return chunks
    
    def chunk_text_with_pages(self, text: str, page_breaks: List[int] = None) -> List[dict]:
        """
        Legacy function: Chunk text preserving page information.
        
        Args:
            text: Full text content
            page_breaks: List of character positions where pages break
        
        Returns:
            List of chunk dicts with page_number included
        """
        chunks = self.chunk_text(text)
        
        if page_breaks:
            for chunk in chunks:
                start_char = chunk["start_char"]
                # Find which page this chunk belongs to
                page_num = 0
                for i, break_pos in enumerate(page_breaks):
                    if start_char >= break_pos:
                        page_num = i + 1
                    else:
                        break
                chunk["page_number"] = page_num
        
        return chunks

