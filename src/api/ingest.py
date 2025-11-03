"""Ingestion API endpoints."""
from flask import Blueprint, request, jsonify, g
from src.auth.supabase_auth import require_auth, get_or_create_user
from src.db.session import get_db_session
from src.db.models import Document, IngestJob
from src.storage.supabase_storage import SupabaseStorage
from src.tasks.worker_upsert_pinecone import process_doc
from src.config import Config
import uuid
from datetime import datetime

ingest_bp = Blueprint("ingest", __name__)


@ingest_bp.route("/upload", methods=["POST"])
@require_auth
def upload_file():
    """Upload file and enqueue ingestion job."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    
    user_info = g.current_user
    user_id = get_or_create_user(user_info["supabase_user_id"], user_info["email"])
    
    db = get_db_session()
    try:
        # Upload to Supabase Storage
        storage = SupabaseStorage()
        file_content = file.read()
        
        # Enforce file size limit
        if len(file_content) > Config.MAX_UPLOAD_BYTES:
            return jsonify({
                "error": f"File size exceeds maximum allowed size of {Config.MAX_UPLOAD_BYTES} bytes ({Config.MAX_UPLOAD_BYTES // (1024*1024)}MB)"
            }), 400
        
        file_type = file.filename.split(".")[-1] if "." in file.filename else "txt"
        storage_path = storage.upload_file(file_content, file.filename, user_id)
        
        # Create document record
        document = Document(
            user_id=user_id,
            title=file.filename,
            source_type="upload",
            source_url=file.filename,
            storage_path=storage_path,
            file_type=file_type,
            status="pending"
        )
        db.add(document)
        db.flush()
        
        # Create ingestion job
        job = IngestJob(
            user_id=user_id,
            document_id=document.id,
            job_type="upload",
            status="queued"
        )
        db.add(job)
        db.commit()
        
        # Enqueue Celery task (new worker using Pinecone integrated embeddings)
        process_doc.delay(job.id)
        
        return jsonify({
            "jobId": job.id,
            "documentId": document.id,
            "status": "queued"
        }), 201
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@ingest_bp.route("/scrape", methods=["POST"])
@require_auth
def scrape_url():
    """Scrape URL and enqueue ingestion job."""
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "URL required"}), 400
    
    url = data["url"]
    user_info = g.current_user
    user_id = get_or_create_user(user_info["supabase_user_id"], user_info["email"])
    
    db = get_db_session()
    try:
        # Create document record
        document = Document(
            user_id=user_id,
            title=url,
            source_type="scrape",
            source_url=url,
            file_type="html",
            status="pending"
        )
        db.add(document)
        db.flush()
        
        # Create ingestion job
        job = IngestJob(
            user_id=user_id,
            document_id=document.id,
            job_type="scrape",
            status="queued"
        )
        db.add(job)
        db.commit()
        
        # Enqueue Celery task (new worker using Pinecone integrated embeddings)
        process_doc.delay(job.id)
        
        return jsonify({
            "jobId": job.id,
            "documentId": document.id,
            "status": "queued"
        }), 201
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@ingest_bp.route("/upload/status", methods=["GET"])
@require_auth
def get_upload_status():
    """Get ingestion job status."""
    job_id = request.args.get("jobId")
    if not job_id:
        return jsonify({"error": "jobId parameter required"}), 400
    
    db = get_db_session()
    try:
        job = db.query(IngestJob).filter(IngestJob.id == job_id).first()
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        # Check if user owns this job
        user_info = g.current_user
        if job.user_id != get_or_create_user(user_info["supabase_user_id"], user_info["email"]):
            return jsonify({"error": "Unauthorized"}), 403
        
        return jsonify({
            "jobId": job.id,
            "status": job.status,
            "progress": job.progress,
            "errorMessage": job.error_message,
            "createdAt": job.created_at.isoformat() if job.created_at else None,
            "updatedAt": job.updated_at.isoformat() if job.updated_at else None
        }), 200
        
    finally:
        db.close()

