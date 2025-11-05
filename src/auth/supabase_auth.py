"""Lightweight auth helper.

This backend no longer verifies Supabase JWTs. Instead, it trusts
`X-User-Id` (and optional `X-User-Email`) headers provided by the caller.
We keep the same user shape used elsewhere (keys include `supabase_user_id`)
to avoid changing downstream code or database schema.
"""
from functools import wraps
from flask import request, jsonify, g


def require_auth(f):
    """Require `X-User-Id` header and attach `g.current_user`.

    Expected headers:
    - X-User-Id: stable external user identifier (string)
    - X-User-Email: optional email for first-time user creation
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id_header = request.headers.get("X-User-Id")
        if not user_id_header:
            return jsonify({"error": "Missing X-User-Id header"}), 401
        # Optional but useful for first user creation
        user_email = request.headers.get("X-User-Email", "")

        # Preserve existing contract expected by API layers
        g.current_user = {
            "user_id": user_id_header,
            "email": user_email,
            "supabase_user_id": user_id_header,
        }
        return f(*args, **kwargs)

    return decorated_function


def get_supabase_client():  # Backwards-compat shim for any lingering imports
    from supabase.client import create_client
    from src.config import Config
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)


def get_user_from_token(_token: str) -> dict:
    """Deprecated. Kept for import compatibility; no longer used."""
    raise ValueError("JWT auth disabled; use X-User-Id header")


def get_or_create_user(supabase_user_id: str, email: str) -> str:
    """Get or create user in database."""
    from src.db.session import get_db_session
    from src.db.models import User
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.supabase_user_id == supabase_user_id).first()
        if not user:
            user = User(supabase_user_id=supabase_user_id, email=email)
            db.add(user)
            db.commit()
        return str(user.id)
    finally:
        db.close()

