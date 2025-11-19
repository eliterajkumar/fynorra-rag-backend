# backend/api/frontend_router.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from services import db
from typing import List, Dict

router = APIRouter()

@router.get("/health")
def health_check():
    """Health check for frontend"""
    return {"status": "ok", "service": "pdf_chatbot"}

@router.get("/sessions")
def get_sessions() -> List[Dict]:
    """Get all active chat sessions"""
    try:
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT session_id, created_at FROM conversations ORDER BY created_at DESC LIMIT 20")
        rows = cur.fetchall()
        conn.close()
        return [{"session_id": r["session_id"], "created_at": r["created_at"]} for r in rows]
    except Exception:
        return []

@router.get("/session/{session_id}/history")
def get_session_history(session_id: str) -> List[Dict]:
    """Get chat history for a session"""
    try:
        messages = db.get_conversation_history(session_id)
        return [{"role": m["role"], "content": m["content"], "timestamp": m["timestamp"]} for m in messages]
    except Exception:
        return []

@router.get("/documents")
def get_uploaded_documents() -> List[Dict]:
    """Get list of uploaded PDF documents"""
    try:
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT pdf_id, filename FROM pdf_documents ORDER BY pdf_id DESC LIMIT 50")
        rows = cur.fetchall()
        conn.close()
        return [{"id": r["pdf_id"], "filename": r["filename"]} for r in rows]
    except Exception:
        return []

@router.delete("/session/{session_id}")
def delete_session(session_id: str):
    """Delete a chat session"""
    try:
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        return {"deleted": deleted > 0, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))