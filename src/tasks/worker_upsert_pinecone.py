"""Celery worker task for document ingestion using Pinecone integrated embeddings."""
from src.tasks.celery_app import celery_app
from src.db.session import get_db_session
from src.db.models import Document, IngestJob, Chunk
from src.ingest.extractor import extract_text_from_pdf_bytes, extract_text_from_url, extract_text_from_html
from src.ingest.chunker import TextChunker
from src.embeddings.pinecone_client import PineconeClient
from src.storage.supabase_storage import SupabaseStorage
from src.config import Config
import traceback
import time


@celery_app.task(bind=True, name="ingest.process_doc")
def process_doc(self, job_id: str):
    """
    Process ingestion job for file uploads and URL scrapes.
    Uses Pinecone integrated embeddings (no local embedding generation).
    
    Args:
        job_id: IngestJob ID
    """
    db = get_db_session()
    job = None
    document = None
    
    try:
        # Fetch job and document
        job = db.query(IngestJob).filter(IngestJob.id == job_id).first()
        if not job:
            return {"status": "error", "message": "Job not found"}
        
        document = db.query(Document).filter(Document.id == job.document_id).first()
        if not document:
            return {"status": "error", "message": "Document not found"}
        
        user_id = job.user_id
        
        # Update job status
        job.status = "processing"
        job.progress = 10
        job.celery_task_id = self.request.id
        db.commit()
        
        pages = []
        
        # Extract pages based on job type
        if job.job_type == "upload" or job.job_type == "file":
            # Download file from storage
            storage = SupabaseStorage()
            file_content = storage.download_file(document.storage_path)
            
            job.progress = 20
            db.commit()
            
            # Extract pages (returns List[str])
            if document.file_type == "pdf" or document.file_type.endswith(".pdf"):
                pages = extract_text_from_pdf_bytes(file_content)
            elif document.file_type in ["html", "htm"] or document.file_type.endswith((".html", ".htm")):
                html_content = file_content.decode("utf-8", errors="ignore")
                pages = extract_text_from_html(html_content)
            elif document.file_type in ["txt", "text"] or document.file_type.endswith(".txt"):
                text = file_content.decode("utf-8", errors="ignore")
                pages = [text]  # Single "page" for text files
            else:
                raise ValueError(f"Unsupported file type: {document.file_type}")
        
        elif job.job_type == "scrape" or job.job_type == "url":
            # Extract from URL
            job.progress = 15
            db.commit()
            
            sections, title = extract_text_from_url(document.source_url)
            pages = sections
            
            if title:
                document.title = title
            
            job.progress = 30
            db.commit()
        else:
            raise ValueError(f"Unknown job type: {job.job_type}")
        
        # Chunk pages
        chunker = TextChunker()
        chunks = chunker.chunk_pages(pages, max_chars=Config.CHUNK_SIZE, overlap=Config.CHUNK_OVERLAP)
        
        job.progress = 50
        db.commit()
        
        if not chunks:
            # No chunks extracted, mark as failed
            job.status = "failed"
            job.error_message = "No text chunks extracted from document"
            document.status = "failed"
            db.commit()
            return {"status": "failed", "message": "No chunks extracted"}
        
        # Build records for Pinecone (text-based, no embeddings)
        records = []
        chunk_objects = []
        
        for chunk in chunks:
            vector_id = f"{document.id}::{chunk['chunk_index']}"
            
            # Prepare record for Pinecone text-based upsert
            rec = {
                "id": vector_id,
                "text": chunk["text"],  # Pinecone will embed this server-side
                "metadata": {
                    "doc_id": document.id,
                    "user_id": user_id,
                    "page": chunk.get("page", 1),
                    "chunk_index": chunk["chunk_index"],
                    "preview": chunk.get("preview", chunk["text"][:200])
                }
            }
            records.append(rec)
            
            # Create chunk object for DB
            chunk_obj = Chunk(
                document_id=document.id,
                chunk_index=chunk["chunk_index"],
                content=chunk["text"],
                start_char=chunk.get("start_char"),
                end_char=chunk.get("end_char"),
                page_number=chunk.get("page", 1),
                pinecone_id=vector_id
            )
            chunk_objects.append(chunk_obj)
        
        job.progress = 60
        db.commit()
        
        # Upsert to Pinecone using text-based API (server-side embedding)
        pinecone = PineconeClient()
        namespace = user_id  # Per-user namespace for isolation
        
        try:
            result = pinecone.upsert_texts(
                namespace=namespace,
                records=records,
                batch_size=Config.BATCH_SIZE
            )
        except Exception as e:
            # Transient error - retry with exponential backoff
            error_msg = str(e)
            if "429" in error_msg or "500" in error_msg or "503" in error_msg:
                # Retryable error
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries), max_retries=3)
            else:
                # Permanent error
                raise
        
        job.progress = 90
        db.commit()
        
        # Save chunks to DB
        db.bulk_save_objects(chunk_objects)
        
        # Update document and job
        document.chunk_count = len(chunks)
        document.status = "completed"
        document.metadata = document.metadata or {}
        document.metadata["pages_count"] = len(pages)
        job.progress = 100
        job.status = "completed"
        db.commit()
        
        return {
            "status": "completed",
            "chunks": len(chunks),
            "pages": len(pages),
            "records_upserted": result.get("records_upserted", len(chunks))
        }
        
    except Exception as e:
        error_msg = str(e)
        traceback.print_exc()
        
        # Update job/document status on error
        if job:
            job.status = "failed"
            job.error_message = error_msg
            db.commit()
        
        if document:
            document.status = "failed"
            db.commit()
        
        # Re-raise to trigger Celery retry if applicable
        raise
    
    finally:
        db.close()


@celery_app.task(bind=True, name="ingest.process_url")
def process_url(self, job_id: str):
    """Alias for process_doc when handling URL scraping."""
    return process_doc(self, job_id)

