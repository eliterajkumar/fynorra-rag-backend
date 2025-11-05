"""Worker for processing uploaded documents and storing embeddings in Pinecone."""
import os
import tempfile
import traceback
from datetime import datetime
from celery import shared_task
import pdfplumber
from bs4 import BeautifulSoup
from src.db.session import get_db_session
from src.db.models import IngestJob, Document
from src.embeddings.pinecone_client import PineconeClient
from src.storage.supabase_storage import SupabaseStorage
from src.config import Config
from openai import OpenAI

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_doc(self, job_id: str):
    """Process uploaded document into embeddings and store in Pinecone."""
    db = get_db_session()
    job = None
    try:
        job = db.query(IngestJob).filter(IngestJob.id == job_id).first()
        if not job:
            return
        
        job.status = "processing"
        job.updated_at = datetime.utcnow()
        db.commit()

        doc = db.query(Document).filter(Document.id == job.document_id).first()
        if not doc:
            raise Exception("Document not found")

        # 1️⃣ Download file from Supabase
        storage = SupabaseStorage()
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        storage.download_file(doc.storage_path, tmp_file.name)

        # 2️⃣ Extract text based on file type
        ext = doc.file_type.lower()
        text_content = ""
        
        if ext == "pdf":
            with pdfplumber.open(tmp_file.name) as pdf:
                text_content = "\n".join([page.extract_text() or "" for page in pdf.pages])
        elif ext in ["txt", "text"]:
            with open(tmp_file.name, 'r', encoding='utf-8') as f:
                text_content = f.read()
        elif ext in ["html", "htm"]:
            with open(tmp_file.name, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                text_content = soup.get_text()
        else:
            raise Exception(f"Unsupported file type: {ext}")

        if not text_content.strip():
            raise Exception("No content extracted from file")

        # 3️⃣ Simple text chunking
        chunk_size = 1000
        overlap = 200
        chunks = []
        
        for i in range(0, len(text_content), chunk_size - overlap):
            chunk_text = text_content[i:i + chunk_size]
            if chunk_text.strip():
                chunks.append(chunk_text)

        # 4️⃣ Generate embeddings
        client = OpenAI(api_key=Config.OPENAI_API_KEY)
        pinecone_client = PineconeClient()

        namespace = f"user-{doc.user_id}"
        vectors = []
        for i, chunk_text in enumerate(chunks):
            text = chunk_text.strip()
            if not text:
                continue
            emb = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            ).data[0].embedding
            vectors.append({
                "id": f"{doc.id}-{i}",
                "values": emb,
                "metadata": {
                    "user_id": str(doc.user_id),
                    "document_id": str(doc.id),
                    "text": text[:1000],
                    "source": doc.source_url or doc.title,
                    "chunk_index": i,
                }
            })

        # 5️⃣ Upsert to Pinecone
        pinecone_client.upsert_vectors(vectors, namespace)

        # 6️⃣ Update job + document status
        job.status = "completed"
        job.progress = 100
        job.updated_at = datetime.utcnow()
        doc.status = "indexed"
        db.commit()

    except Exception as e:
        db.rollback()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.updated_at = datetime.utcnow()
            db.commit()
        print("❌ Error in process_doc:", e)
        traceback.print_exc()
    finally:
        db.close()
        if 'tmp_file' in locals() and os.path.exists(tmp_file.name):
            os.unlink(tmp_file.name)
