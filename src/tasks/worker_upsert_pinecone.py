"""Worker for processing uploaded documents and storing embeddings in Pinecone."""
import os
import tempfile
import traceback
from datetime import datetime
from celery import shared_task
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, UnstructuredHTMLLoader, UnstructuredWordDocumentLoader
)
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

        # 2️⃣ Choose loader based on file type
        ext = doc.file_type.lower()
        if ext in ["pdf"]:
            loader = PyPDFLoader(tmp_file.name)
        elif ext in ["txt", "text"]:
            loader = TextLoader(tmp_file.name)
        elif ext in ["html", "htm"]:
            loader = UnstructuredHTMLLoader(tmp_file.name)
        elif ext in ["doc", "docx"]:
            loader = UnstructuredWordDocumentLoader(tmp_file.name)
        else:
            raise Exception(f"Unsupported file type: {ext}")

        documents = loader.load()
        if not documents:
            raise Exception("No content extracted from file")

        # 3️⃣ Chunk text
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(documents)

        # 4️⃣ Generate embeddings
        client = OpenAI(api_key=Config.OPENAI_API_KEY)
        pinecone_client = PineconeClient()

        namespace = f"user-{doc.user_id}"
        vectors = []
        for i, chunk in enumerate(chunks):
            text = chunk.page_content.strip()
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
