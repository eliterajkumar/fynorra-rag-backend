"""
Brain API endpoints for document management (improved).
- GET /brain?limit=&offset=
- GET /brain/<doc_id>/vectors?limit=&offset=
Assumptions:
- require_auth sets g.current_user with keys "supabase_user_id" and "email"
- get_or_create_user(supabase_user_id, email) returns internal user_id used in Document.user_id
"""

import logging
from flask import Blueprint, request, jsonify, g
from src.auth.supabase_auth import require_auth, get_or_create_user
from src.db.session import get_db_session
from src.db.models import Document, Chunk
from sqlalchemy import func
from sqlalchemy.orm import load_only
from uuid import UUID

logger = logging.getLogger(__name__)
brain_bp = Blueprint("brain", __name__)

# constants
DEFAULT_LIMIT = 20
MAX_LIMIT = 200
CHUNK_PREVIEW_LEN = 400  # smaller preview for privacy & response size


def _parse_pagination_args():
    try:
        limit = int(request.args.get("limit", DEFAULT_LIMIT))
    except Exception:
        limit = DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))
    try:
        offset = int(request.args.get("offset", 0))
    except Exception:
        offset = 0
    offset = max(0, offset)
    return limit, offset


@brain_bp.route("/brain", methods=["GET"])
@require_auth
def get_brain():
    """List user documents and vector stats. Paginated."""
    user_info = getattr(g, "current_user", None)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_session()
    limit, offset = _parse_pagination_args()

    try:
        user_id = get_or_create_user(user_info["supabase_user_id"], user_info.get("email"))
        # Query documents with pagination
        q = db.query(Document).filter(Document.user_id == user_id).order_by(Document.created_at.desc())
        total_documents = q.count()
        documents = q.offset(offset).limit(limit).all()

        # Total chunk count (single aggregated query)
        total_chunks = db.query(func.count(Chunk.id)).join(Document).filter(Document.user_id == user_id).scalar() or 0

        docs_data = []
        for doc in documents:
            docs_data.append({
                "id": str(doc.id),
                "title": doc.title,
                "sourceType": doc.source_type,
                "sourceUrl": doc.source_url,
                "fileType": doc.file_type,
                "chunkCount": doc.chunk_count or 0,
                "status": doc.status,
                "createdAt": doc.created_at.isoformat() if doc.created_at is not None else None,
                "updatedAt": doc.updated_at.isoformat() if doc.updated_at is not None else None
            })

        return jsonify({
            "documents": docs_data,
            "totalDocuments": total_documents,
            "totalChunks": int(total_chunks),
            "totalVectors": int(total_chunks),  # approximate: one vector per chunk
            "limit": limit,
            "offset": offset
        }), 200

    except Exception as e:
        logger.exception("Error in get_brain")
        db.rollback()
        return jsonify({"error": "Internal server error"}), 500
    finally:
        db.close()


@brain_bp.route("/brain/<doc_id>/vectors", methods=["GET"])
@require_auth
def get_document_vectors(doc_id: str):
    """Preview chunks for a document. Supports pagination."""
    user_info = getattr(g, "current_user", None)
    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401

    # validate doc_id (if you use UUIDs)
    try:
        # Optionally validate UUID; if your ids are ints, skip this
        UUID(doc_id, version=4)
    except Exception:
        # not a UUID — continue; if your system uses ints, you can try int(doc_id) instead
        pass

    limit, offset = _parse_pagination_args()
    db = get_db_session()

    try:
        user_id = get_or_create_user(user_info["supabase_user_id"], user_info.get("email"))

        # Ensure the document belongs to the user
        document = db.query(Document).filter(
            Document.id == doc_id,
            Document.user_id == user_id
        ).first()

        if not document:
            return jsonify({"error": "Document not found"}), 404

        # Get paginated chunks (only select small fields to reduce memory)
        chunks_q = db.query(Chunk).filter(Chunk.document_id == doc_id).order_by(Chunk.chunk_index)
        total_chunks = chunks_q.count()
        chunks = chunks_q.offset(offset).limit(limit).all()

        chunks_data = []
        for chunk in chunks:
            snippet = (chunk.content or "")[:CHUNK_PREVIEW_LEN]
            chunks_data.append({
                "id": str(chunk.id),
                "chunkIndex": chunk.chunk_index,
                "contentPreview": snippet,
                "startChar": chunk.start_char,
                "endChar": chunk.end_char,
                "pageNumber": chunk.page_number,
                "pineconeId": chunk.pinecone_id
            })

        return jsonify({
            "documentId": str(doc_id),
            "title": document.title,
            "chunks": chunks_data,
            "totalChunks": total_chunks,
            "limit": limit,
            "offset": offset
        }), 200

    except Exception as e:
        logger.exception("Error in get_document_vectors for doc_id=%s", doc_id)
        db.rollback()
        return jsonify({"error": "Internal server error"}), 500
    finally:
        db.close()
