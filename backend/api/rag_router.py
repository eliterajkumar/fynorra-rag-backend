# backend/api/rag_router.py
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import os
import logging
from typing import List

from services import llm_handler, db, pdf_processor

router = APIRouter()
logger = logging.getLogger("rag_router")

# Simple system prompt for PDF chatbot
BASE_PERSONA = (
    "You are a helpful AI assistant that answers questions based on uploaded PDF documents. "
    "Answer the user's question using only the information provided in the context. "
    "If the information is not available in the context, say so clearly. "
    "Keep your answers concise and relevant."
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
    """Chat with uploaded PDFs"""
    body = await request.json()
    message_text = body.get("message", "").strip()
    session_id = body.get("session_id")
    
    if not message_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Search PDF documents
    pdf_hits = db.search_pdf_documents(message_text, top_k=3) or []
    
    if not pdf_hits:
        return JSONResponse({
            "reply": "I couldn't find relevant information in the uploaded PDFs for your question. Please upload PDFs first.",
            "session_id": session_id or "default"
        })
    
    # Build context from PDF hits
    sources_parts = []
    for h in pdf_hits:
        filename = h.get("filename", "Unknown")
        text = h.get("text") or ""
        sources_parts.append(f"[PDF: {filename}]\n{text[:1200]}")
    
    context = "\n\n".join(sources_parts)
    
    try:
        # Get LLM response
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
        
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return JSONResponse({
            "reply": "Sorry, I encountered an error processing your question. Please try again.",
            "error": str(e)
        }, status_code=500)