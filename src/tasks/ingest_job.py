"""Celery tasks for document ingestion."""
from src.tasks.celery_app import celery_app
from src.db.session import get_db_session
from src.db.models import Document, IngestJob, Chunk, User
from src.ingest.extractor import extract_text_from_file, extract_text_from_url
from src.ingest.chunker import TextChunker
from src.embeddings.adapter import EmbeddingAdapter
from src.embeddings.pinecone_client import PineconeClient
from src.storage.supabase_storage import SupabaseStorage
from src.security.crypto import decrypt_api_key
import traceback


@celery_app.task(bind=True, name="ingest.upload_file")
def ingest_upload_file_task(self, job_id: str, document_id: str, user_id: str):
    """Process file upload ingestion."""
    db = get_db_session()
    try:
        job = db.query(IngestJob).filter(IngestJob.id == job_id).first()
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not job or not document:
            return {"status": "error", "message": "Job or document not found"}
        
        # Update job status
        job.status = "processing"
        job.progress = 10
        job.celery_task_id = self.request.id
        db.commit()
        
        # Download file from storage
        storage = SupabaseStorage()
        file_content = storage.download_file(document.storage_path)
        
        job.progress = 20
        db.commit()
        
        # Extract text
        text = extract_text_from_file(file_content, document.file_type)
        
        job.progress = 40
        db.commit()
        
        # Chunk text
        chunker = TextChunker()
        chunks = chunker.chunk_text(text)
        
        job.progress = 50
        db.commit()
        
        # Generate embeddings
        embedding_adapter = EmbeddingAdapter()
        chunk_contents = [chunk["content"] for chunk in chunks]
        embeddings = embedding_adapter.embed_texts(chunk_contents)
        
        job.progress = 70
        db.commit()
        
        # Upsert to Pinecone
        pinecone = PineconeClient()
        vectors = []
        chunk_objects = []
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = f"{document_id}_{i}"
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "user_id": user_id,
                    "document_id": document_id,
                    "chunk_index": i,
                    "start_char": chunk.get("start_char"),
                    "end_char": chunk.get("end_char"),
                    "page_number": chunk.get("page_number"),
                    "content": chunk["content"][:500]  # Store snippet
                }
            })
            
            chunk_obj = Chunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk["content"],
                start_char=chunk.get("start_char"),
                end_char=chunk.get("end_char"),
                page_number=chunk.get("page_number"),
                pinecone_id=vector_id
            )
            chunk_objects.append(chunk_obj)
        
        # Batch upsert
        pinecone.upsert_vectors(vectors)
        
        # Save chunks to DB
        db.bulk_save_objects(chunk_objects)
        
        # Update document and job
        document.chunk_count = len(chunks)
        document.status = "completed"
        job.progress = 100
        job.status = "completed"
        db.commit()
        
        return {"status": "completed", "chunks": len(chunks)}
        
    except Exception as e:
        error_msg = str(e)
        traceback.print_exc()
        
        if job:
            job.status = "failed"
            job.error_message = error_msg
            db.commit()
        
        if document:
            document.status = "failed"
            db.commit()
        
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="ingest.scrape_url")
def ingest_scrape_url_task(self, job_id: str, document_id: str, user_id: str, url: str):
    """Process URL scraping ingestion."""
    db = get_db_session()
    job = None
    document = None
    
    try:
        job = db.query(IngestJob).filter(IngestJob.id == job_id).first()
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not job or not document:
            return {"status": "error", "message": "Job or document not found"}
        
        job.status = "processing"
        job.progress = 10
        job.celery_task_id = self.request.id
        db.commit()
        
        # Scrape URL
        text, title = extract_text_from_url(url)
        
        if title:
            document.title = title
        
        job.progress = 30
        db.commit()
        
        # Chunk text
        chunker = TextChunker()
        chunks = chunker.chunk_text(text)
        
        job.progress = 50
        db.commit()
        
        # Generate embeddings
        embedding_adapter = EmbeddingAdapter()
        chunk_contents = [chunk["content"] for chunk in chunks]
        embeddings = embedding_adapter.embed_texts(chunk_contents)
        
        job.progress = 70
        db.commit()
        
        # Upsert to Pinecone
        pinecone = PineconeClient()
        vectors = []
        chunk_objects = []
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = f"{document_id}_{i}"
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "user_id": user_id,
                    "document_id": document_id,
                    "chunk_index": i,
                    "start_char": chunk.get("start_char"),
                    "end_char": chunk.get("end_char"),
                    "url": url
                }
            })
            
            chunk_obj = Chunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk["content"],
                start_char=chunk.get("start_char"),
                end_char=chunk.get("end_char"),
                pinecone_id=vector_id
            )
            chunk_objects.append(chunk_obj)
        
        pinecone.upsert_vectors(vectors)
        db.bulk_save_objects(chunk_objects)
        
        document.chunk_count = len(chunks)
        document.status = "completed"
        job.progress = 100
        job.status = "completed"
        db.commit()
        
        return {"status": "completed", "chunks": len(chunks)}
        
    except Exception as e:
        error_msg = str(e)
        traceback.print_exc()
        
        if job:
            job.status = "failed"
            job.error_message = error_msg
            db.commit()
        
        if document:
            document.status = "failed"
            db.commit()
        
        raise
    finally:
        db.close()

