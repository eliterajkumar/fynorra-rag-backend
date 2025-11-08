# main.py
import os
from typing import Optional
from fastapi import FastAPI, UploadFile, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# CORS — allow your frontend domain(s)
FRONTEND_ORIGINS = [
    "https://fynorra.com",
    "http://localhost:3000",
]

# Env (must be set in Render / locally)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "your_document_bucket")
PORT = int(os.environ.get("PORT", 8000))

# Validate
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY environment variables")

# App init
app = FastAPI(title="Fynorra RAG Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy import processor to keep startup light
from document_processor import (
    extract_text_from_pdf_bytes,
    chunk_text,
    generate_embeddings,
    save_chunks_to_supabase,
    retrieve_relevant_chunks,
    answer_question_with_context,  # uses OpenRouter
)

@app.post("/upload")
async def upload_file(
    file: UploadFile,
    project: Optional[str] = Form("demo"),
    user_id: Optional[str] = Form("anonymous")
):
    """
    Receives file (form-data), uploads to Supabase Storage, extracts text,
    chunks, generates embeddings, and stores chunks in `messages` table.
    """
    try:
        file_bytes = await file.read()
        filename = file.filename or "upload"
        # 1) Upload to Supabase Storage
        storage_path = f"uploads/{user_id}/{filename}"
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        try:
            # Try upload first, if file exists, remove and re-upload
            try:
                upload_res = supabase.storage.from_(SUPABASE_BUCKET).upload(storage_path, file_bytes)
            except:
                supabase.storage.from_(SUPABASE_BUCKET).remove([storage_path])
                upload_res = supabase.storage.from_(SUPABASE_BUCKET).upload(storage_path, file_bytes)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")

        # 2) Extract text
        if filename.lower().endswith(".pdf"):
            text = extract_text_from_pdf_bytes(file_bytes)
        else:
            try:
                text = file_bytes.decode("utf-8")
            except Exception:
                text = file_bytes.decode("latin1", errors="ignore")

        # 3) Chunk & embed & save
        chunks = chunk_text(text, size=800, overlap=100)
        if not chunks:
            return {"status": "no_text", "message": "No textual content found in file."}

        embeddings = generate_embeddings(chunks)
        try:
            save_chunks_to_supabase(project, user_id, filename, chunks, embeddings)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Save error: {str(e)}")

        return {
            "status": "success",
            "project": project,
            "filename": filename,
            "chunks_saved": len(chunks),
            "storage_path": storage_path
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Fynorra RAG Backend"}

@app.post("/ask")
async def ask(payload: dict = Body(...)):
    """
    POST JSON: { "project": "demo", "question": "What is X?", "top_k": 5 }
    Uses stored embeddings + OpenRouter LLM (env vars) and returns answer text.
    """
    project = payload.get("project", "demo")
    question = payload.get("question", "")
    top_k = int(payload.get("top_k", 5))

    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="`question` is required")

    answer, err = answer_question_with_context(project, question, top_k=top_k)
    if err:
        raise HTTPException(status_code=500, detail=err)
    return {"answer": answer}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
