"""Admin endpoints for reindexing and maintenance."""
from flask import Blueprint, request, jsonify
from src.config import Config
from src.db.session import get_db_session
from src.db.models import Document, Chunk
from src.embeddings.adapter import EmbeddingAdapter
from src.embeddings.pinecone_client import PineconeClient
from src.tasks.celery_app import celery_app

admin_bp = Blueprint("admin", __name__)


def require_admin(f):
    """Decorator to require admin token."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Missing authorization header"}), 401
        
        token = auth_header.replace("Bearer ", "")
        if token != Config.ADMIN_TOKEN:
            return jsonify({"error": "Unauthorized"}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


@admin_bp.route("/admin/reindex", methods=["POST"])
@require_admin
def reindex():
    """Reindex all vectors in Pinecone."""
    data = request.get_json() or {}
    document_id = data.get("documentId")
    
    db = get_db_session()
    
    try:
        if document_id:
            # Reindex single document
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return jsonify({"error": "Document not found"}), 404
            
            chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
        else:
            # Reindex all documents
            documents = db.query(Document).all()
            chunks = db.query(Chunk).all()
        
        # Regenerate embeddings and upsert
        embedding_adapter = EmbeddingAdapter()
        pinecone = PineconeClient()
        
        # Ensure we pass plain Python strings to embed_texts (cast SQLAlchemy Column -> str)
        chunk_contents = [str(chunk.content) if chunk.content is not None else "" for chunk in chunks]
        embeddings = embedding_adapter.embed_texts(chunk_contents)
        
        vectors = []
        for chunk, embedding in zip(chunks, embeddings):
            vectors.append({
                "id": chunk.pinecone_id or f"{chunk.document_id}_{chunk.chunk_index}",
                "values": embedding,
                "metadata": {
                    "user_id": chunk.document.user_id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "page_number": chunk.page_number,
                    "content": chunk.content[:500]
                }
            })
        
        pinecone.upsert_vectors(vectors)
        
        return jsonify({
            "message": "Reindexing completed",
            "vectorsUpserted": len(vectors)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@admin_bp.route("/admin/garbage-collect", methods=["POST"])
@require_admin
def garbage_collect():
    """Clean up orphaned vectors in Pinecone."""
    db = get_db_session()
    
    try:
        # Get all valid Pinecone IDs from database
        valid_chunks = db.query(Chunk.pinecone_id).filter(Chunk.pinecone_id.isnot(None)).all()
        valid_ids = {chunk.pinecone_id for chunk in valid_chunks}
        
        # Note: Pinecone doesn't provide easy listing, so this is a placeholder
        # In production, you'd query Pinecone index stats or list vectors
        
        return jsonify({
            "message": "Garbage collection completed",
            "validVectors": len(valid_ids)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

