"""Query API endpoint for RAG."""
from flask import Blueprint, request, jsonify, g
from src.auth.supabase_auth import require_auth, get_or_create_user
from src.embeddings.pinecone_client import PineconeClient
from src.llm.provider import LLMProvider
from src.db.session import get_db_session
from src.db.models import UserSettings, Document
from src.config import Config

query_bp = Blueprint("query", __name__)


@query_bp.route("/query", methods=["POST"])
@require_auth
def query_rag():
    """Query RAG system and get AI answer with citations."""
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "query field required"}), 400
    
    query_text = data["query"]
    top_k = data.get("top_k", Config.TOP_K)
    
    user_info = g.current_user
    db = get_db_session()
    
    try:
        user_id = get_or_create_user(user_info["supabase_user_id"], user_info["email"])
        
        # Get user settings for custom LLM keys (embedding keys no longer needed)
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        
        # Query Pinecone using text (server-side embedding)
        pinecone = PineconeClient()
        namespace = user_id  # Per-user namespace
        filter_dict = {"user_id": user_id}
        matches = pinecone.query_text(
            namespace=namespace,
            text=query_text,
            top_k=top_k,
            include_metadata=True,
            filter_dict=filter_dict
        )
        
        if not matches:
            return jsonify({
                "answer": "I couldn't find any relevant information in your documents.",
                "sources": [],
                "tokensUsed": 0
            }), 200
        
        # Build context from retrieved chunks
        context_parts = []
        sources = []
        seen_doc_ids = set()
        
        for match in matches:
            metadata = match.get("metadata", {})
            doc_id = metadata.get("doc_id") or metadata.get("document_id")  # Support both field names
            chunk_preview = metadata.get("preview", "")
            
            if doc_id and doc_id not in seen_doc_ids:
                doc = db.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    sources.append({
                        "documentId": doc.id,
                        "title": doc.title,
                        "score": match.get("score", 0),
                        "chunkIndex": metadata.get("chunk_index"),
                        "pageNumber": metadata.get("page", metadata.get("page_number"))
                    })
                    seen_doc_ids.add(doc_id)
            
            # Use preview from metadata, fallback to empty if not available
            if chunk_preview:
                context_parts.append(chunk_preview)
        
        context = "\n\n".join(context_parts)
        
        # Build RAG prompt
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that answers questions based on the provided context. Always cite your sources when possible."
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query_text}\n\nAnswer the question based on the context above. If the context doesn't contain enough information, say so."
            }
        ]
        
        # Call LLM (default to OpenRouter unless user settings override)
        llm_provider = LLMProvider(
            custom_api_key_encrypted=settings.custom_llm_api_key_encrypted if settings else None,
            provider=settings.preferred_llm_provider if settings else "openrouter"
        )
        
        answer = llm_provider.chat_completion(messages, max_tokens=Config.MAX_TOKENS)
        
        # Estimate tokens (rough approximation)
        tokens_used = len(query_text.split()) + len(answer.split()) + len(context.split())
        
        return jsonify({
            "answer": answer,
            "sources": sources,
            "tokensUsed": tokens_used
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

