# backend/services/pdf_processor.py
import os
import uuid
from pathlib import Path
from typing import List, Dict
import PyPDF2
import logging

logger = logging.getLogger(__name__)

# Ensure uploads directory is always in backend folder
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""

def save_uploaded_pdf(file_content: bytes, filename: str) -> Dict:
    """Save uploaded PDF and extract text"""
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}_{filename}"
    
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    text_content = extract_text_from_pdf(str(file_path))
    
    return {
        "id": file_id,
        "filename": filename,
        "path": str(file_path),
        "text": text_content,
        "size": len(file_content)
    }

def chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
    """Split text into chunks for better processing"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    
    for word in words:
        if current_size + len(word) > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_size = len(word)
        else:
            current_chunk.append(word)
            current_size += len(word) + 1
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

def search_in_pdfs(query: str, pdf_texts: List[Dict], max_chunks: int = 3) -> List[str]:
    """Simple keyword-based search in PDF texts"""
    query_words = query.lower().split()
    relevant_chunks = []
    
    for pdf in pdf_texts:
        text = pdf.get("text", "")
        chunks = chunk_text(text)
        
        for chunk in chunks:
            chunk_lower = chunk.lower()
            score = sum(1 for word in query_words if word in chunk_lower)
            
            if score > 0:
                relevant_chunks.append({
                    "text": chunk[:800],  # Limit chunk size
                    "filename": pdf.get("filename", ""),
                    "score": score
                })
    
    # Sort by relevance and return top chunks
    relevant_chunks.sort(key=lambda x: x["score"], reverse=True)
    return [f"[{chunk['filename']}] {chunk['text']}" for chunk in relevant_chunks[:max_chunks]]