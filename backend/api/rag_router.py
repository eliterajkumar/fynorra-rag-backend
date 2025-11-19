# backend/api/rag_router.py
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import os
import logging
from typing import List

from services import llm_handler, db, pdf_processor

router = APIRouter()
logger = logging.getLogger("rag_router")

# Friendly AI assistant persona
BASE_PERSONA = (
    "You are a friendly and helpful AI assistant. You can answer general questions and also help with uploaded PDF documents. "
    "When users ask general questions (greetings, general knowledge, etc.), respond naturally and helpfully. "
    "When users ask about uploaded PDFs, use the provided context to answer. "
    "Always maintain a friendly tone and ask how you can help further. "
    "Be conversational and supportive."
)

GENERAL_PERSONA = (
    "You are a friendly and helpful AI assistant. Answer the user's question naturally and helpfully. "
    "Maintain a conversational tone and offer to help with more questions. "
    "You can help with general knowledge, explanations, advice, and more."
)

@router.post("/upload-pdfs")
async def upload_pdfs(files: List[UploadFile] = File(...)):
    """Upload and process multiple PDFs for RAG"""
    if len(files) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 PDFs allowed")
    
    processed_pdfs = []
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files allowed")
        
        content = await file.read()
        pdf_data = pdf_processor.save_uploaded_pdf(content, file.filename)
        
        # Store in database for RAG
        db.save_pdf_document(
            pdf_id=pdf_data["id"],
            filename=pdf_data["filename"],
            text_content=pdf_data["text"]
        )
        
        processed_pdfs.append({
            "id": pdf_data["id"],
            "filename": pdf_data["filename"],
            "size": pdf_data["size"]
        })
    
    return JSONResponse({
        "message": f"{len(processed_pdfs)} PDFs processed and indexed",
        "files": processed_pdfs
    })

@router.post("/chat")
async def chat_endpoint(request: Request):
    """Chat with AI assistant - handles both general questions and PDF queries"""
    body = await request.json()
    message_text = body.get("message", "").strip()
    session_id = body.get("session_id")
    
    if not message_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Search PDF documents
    pdf_hits = db.search_pdf_documents(message_text, top_k=3) or []
    
    try:
        if pdf_hits:
            # User question relates to uploaded PDFs
            sources_parts = []
            for h in pdf_hits:
                filename = h.get("filename", "Unknown")
                text = h.get("text") or ""
                sources_parts.append(f"[PDF: {filename}]\n{text[:1200]}")
            
            context = "\n\n".join(sources_parts)
            
            reply = llm_handler.get_llm_response(
                system_prompt=BASE_PERSONA,
                context=context,
                user_question=message_text,
                request_type="pdf"
            )
            
            return JSONResponse({
                "reply": reply,
                "session_id": session_id or "default",
                "sources": len(pdf_hits)
            })
        else:
            # General question - no PDF context needed
            reply = llm_handler.get_llm_response(
                system_prompt=GENERAL_PERSONA,
                context="",
                user_question=message_text,
                request_type="chat"
            )
            
            return JSONResponse({
                "reply": reply,
                "session_id": session_id or "default",
                "sources": 0
            })
        
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return JSONResponse({
            "reply": "माफ करें, मुझे आपके सवाल का जवाब देने में कुछ तकनीकी समस्या हो रही है। कृपया दोबारा कोशिश करें। मैं आपकी कैसे मदद कर सकता हूं?",
            "error": str(e)
        }, status_code=500)