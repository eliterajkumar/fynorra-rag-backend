"""Settings API endpoints."""
from flask import Blueprint, request, jsonify, g
from src.auth.supabase_auth import require_auth, get_or_create_user
from src.db.session import get_db_session
from src.db.models import UserSettings
from src.security.crypto import encrypt_api_key

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/user/settings", methods=["GET"])
@require_auth
def get_settings():
    """Get user settings."""
    user_info = g.current_user
    db = get_db_session()
    
    try:
        user_id = get_or_create_user(user_info["supabase_user_id"], user_info["email"])
        
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        
        if not settings:
            # Create default settings
            settings = UserSettings(user_id=user_id)
            db.add(settings)
            db.commit()
        
        return jsonify({
            "preferredLLMProvider": settings.preferred_llm_provider,
            "hasCustomLLMKey": bool(settings.custom_llm_api_key_encrypted),
            "hasCustomEmbeddingKey": bool(settings.custom_embedding_api_key_encrypted),
            "metadata": settings.metadata or {}
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@settings_bp.route("/user/settings", methods=["POST"])
@require_auth
def update_settings():
    """Update user settings (encrypt API keys)."""
    user_info = g.current_user
    data = request.get_json()
    
    db = get_db_session()
    
    try:
        user_id = get_or_create_user(user_info["supabase_user_id"], user_info["email"])
        
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        
        if not settings:
            settings = UserSettings(user_id=user_id)
            db.add(settings)
        
        # Update fields
        if "customLLMAPIKey" in data:
            if data["customLLMAPIKey"]:
                settings.custom_llm_api_key_encrypted = str(encrypt_api_key(data["customLLMAPIKey"]))
            else:
                settings.custom_llm_api_key_encrypted = None
        
        if "customEmbeddingAPIKey" in data:
            if data["customEmbeddingAPIKey"]:
                settings.custom_embedding_api_key_encrypted = encrypt_api_key(data["customEmbeddingAPIKey"])
            else:
                settings.custom_embedding_api_key_encrypted = None
        
        if "preferredLLMProvider" in data:
            settings.preferred_llm_provider = data["preferredLLMProvider"]
        
        if "metadata" in data:
            settings.metadata = data["metadata"]
        
        db.commit()
        
        return jsonify({
            "message": "Settings updated",
            "preferredLLMProvider": settings.preferred_llm_provider,
            "hasCustomLLMKey": bool(settings.custom_llm_api_key_encrypted),
            "hasCustomEmbeddingKey": bool(settings.custom_embedding_api_key_encrypted)
        }), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

