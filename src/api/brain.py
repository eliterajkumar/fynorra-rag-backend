"""Brain API endpoints for document management."""
from flask import Blueprint, request, jsonify, g
from src.auth.supabase_auth import require_auth, get_or_create_user
from src.db.session import get_db_session
from src.db.models import Document, Chunk
from src.embeddings.pinecone_client import PineconeClient
from sqlalchemy import func

brain_bp = Blueprint("brain", __name__)


@brain_bp.route("/brain", methods=["GET"])
@require_auth
def get_brain():
    """List user documents and vector stats."""
    user_info = g.current_user
    db = get_db_session()
    
    try:
        user_id = get_or_create_user(user_info["supabase_user_id"], user_info["email"])
        
        # Get all documents for user
        documents = db.query(Document).filter(Document.user_id == user_id).all()
        
        # Get total chunk count
        total_chunks = db.query(func.count(Chunk.id)).join(Document).filter(Document.user_id == user_id).scalar() or 0
        
        # Get Pinecone stats (approximate)
        pinecone = PineconeClient()
        # Note: Pinecone doesn't provide easy user-level stats, so we estimate from DB
        
        docs_data = []
        for doc in documents:
            docs_data.append({
                "id": doc.id,
                "title": doc.title,
                "sourceType": doc.source_type,
                "sourceUrl": doc.source_url,
                "fileType": doc.file_type,
                "chunkCount": doc.chunk_count,
                "status": doc.status,
                "createdAt": doc.created_at.isoformat() if doc.created_at else None,
                "updatedAt": doc.updated_at.isoformat() if doc.updated_at else None
            })
        
        return jsonify({
            "documents": docs_data,
            "totalDocuments": len(docs_data),
            "totalChunks": total_chunks,
            "totalVectors": total_chunks  # Approximate
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@brain_bp.route("/brain/<doc_id>/vectors", methods=["GET"])
@require_auth
def get_document_vectors(doc_id: str):
    """Preview chunks for a document."""
    user_info = g.current_user
    db = get_db_session()
    
    try:
        user_id = get_or_create_user(user_info["supabase_user_id"], user_info["email"])
        
        # Get document
        document = db.query(Document).filter(
            Document.id == doc_id,
            Document.user_id == user_id
        ).first()
        
        if not document:
            return jsonify({"error": "Document not found"}), 404
        
        # Get chunks
        chunks = db.query(Chunk).filter(Chunk.document_id == doc_id).order_by(Chunk.chunk_index).all()
        
        chunks_data = []
        for chunk in chunks:
            chunks_data.append({
                "id": chunk.id,
                "chunkIndex": chunk.chunk_index,
                "content": chunk.content[:500],  # Preview
                "startChar": chunk.start_char,
                "endChar": chunk.end_char,
                "pageNumber": chunk.page_number,
                "pineconeId": chunk.pinecone_id
            })
        
        return jsonify({
            "documentId": doc_id,
            "title": document.title,
            "chunks": chunks_data,
            "totalChunks": len(chunks_data)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

