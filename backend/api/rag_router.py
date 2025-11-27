# backend/api/rag_router.py
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import os
import logging
from typing import List

from services import llm_handler, db, pdf_processor

router = APIRouter()
logger = logging.getLogger("rag_router")

def format_response(response: str) -> str:
    """Clean and format AI response for better presentation with strict length limits"""
    if not response:
        return "Sorry, I couldn't generate a response. Please try again! 😅"
    
    # Remove excessive whitespace and clean up
    response = response.strip()
    
    # Remove any markdown formatting that might look messy
    response = response.replace('**', '')
    response = response.replace('###', '')
    response = response.replace('##', '')
    
    # Ensure it doesn't start with redundant phrases
    redundant_starts = [
        "Based on the provided context,",
        "According to the document,",
        "From the information provided,",
        "The document states that,"
    ]
    
    for start in redundant_starts:
        if response.startswith(start):
            response = response[len(start):].strip()
    
    # STRICT CHARACTER LIMIT - Max 400 characters
    if len(response) > 400:
        # Find last complete sentence within limit
        truncated = response[:400]
        last_sentence_end = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?')
        )
        if last_sentence_end > 200:  # Ensure we have at least 200 chars
            response = truncated[:last_sentence_end + 1]
        else:
            response = truncated[:380] + "..."
    
    # Ensure proper sentence structure
    if not response.endswith(('.', '!', '?', '✨', '😊', '😄', '😅', '...')):
        response += "."
    
    return response

# PDF-focused AI assistant persona with strict length limits
BASE_PERSONA = (
    "You are a PDF document assistant that ONLY answers questions based on uploaded PDF content. "
    "ULTRA STRICT RULES:\n"
    "1. ONLY answer if the question relates to the provided PDF context\n"
    "2. Keep responses EXTREMELY SHORT - Maximum 2-3 sentences, 300 characters max\n"
    "3. Use 1-2 relevant emojis only 📄\n"
    "4. Sound conversational like ChatGPT, not robotic\n"
    "5. NO need to mention 'According to document' - just give direct answer\n"
    "6. End with brief follow-up question (optional)\n"
    "7. Use Hindi/English mix naturally if user uses Hindi\n"
    "8. Be CONCISE - every word counts!"
)

# Only PDF-focused responses are supported now

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
                # Extract more relevant chunks and clean them
                clean_text = text.replace('\n', ' ').replace('\r', ' ').strip()
                sources_parts.append(f"From {filename}: {clean_text[:800]}")
            
            context = "\n\n".join(sources_parts)
            
            # Add strict instruction for PDF-only response
            enhanced_question = f"{message_text}\n\nIMPORTANT: Only answer if this question is related to the PDF content provided above. If the question is about general topics, greetings, or unrelated matters, politely decline. Use emojis and keep it brief but informative based on PDF content only."
            
            reply = llm_handler.get_llm_response(
                system_prompt=BASE_PERSONA,
                context=context,
                user_question=enhanced_question,
                request_type="pdf"
            )
            
            # Clean and format the response
            formatted_reply = format_response(reply)
            
            return JSONResponse({
                "reply": formatted_reply,
                "session_id": session_id or "default",
                "sources": len(pdf_hits)
            })
        else:
            # No PDF context found - politely decline to answer general questions
            polite_decline = (
                "मुझे खुशी होगी आपकी मदद करने में! 😊 लेकिन मैं केवल uploaded PDF documents के बारे में ही जवाब दे सकता हूँ। "
                "कृपया पहले कोई PDF upload करें और फिर उससे related questions पूछें। 📄"
            )
            
            return JSONResponse({
                "reply": polite_decline,
                "session_id": session_id or "default",
                "sources": 0
            })
        
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return JSONResponse({
            "reply": "माफ करें, मुझे आपके सवाल का जवाब देने में कुछ तकनीकी समस्या हो रही है। कृपया दोबारा कोशिश करें। मैं आपकी कैसे मदद कर सकता हूं?",
            "error": str(e)
        }, status_code=500)