# app.py
import os, uuid, time, threading, json, shutil
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import tempfile
import requests

# PDF parsing and text utilities
from PyPDF2 import PdfReader

# LangChain utilities
from langchain_text_splitters import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

# FAISS vector store via langchain
from langchain_community.vectorstores import FAISS

# -------------------------
# CONFIG
# -------------------------
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY not set; OpenRouter calls will fail until provided in env.")

BASE_DIR = Path("data")
UPLOAD_DIR = BASE_DIR / "uploads"
INDEX_DIR = BASE_DIR / "indexes"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # small, fast
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

text_splitter = CharacterTextSplitter(chunk_size=800, chunk_overlap=100)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------------
# Helpers
# -------------------------
def extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    texts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            texts.append(text)
    return "\n".join(texts)

def schedule_delete(session_id: str, delay_seconds: int = 300):
    """Delete uploaded file and index after delay_seconds (default 5 minutes)."""
    def _delete():
        time.sleep(delay_seconds)
        fp = UPLOAD_DIR / f"{session_id}.pdf"
        idxdir = INDEX_DIR / session_id
        try:
            if fp.exists():
                fp.unlink()
            if idxdir.exists():
                shutil.rmtree(idxdir)
            print(f"[cleanup] deleted session {session_id}")
        except Exception as e:
            print("Cleanup error:", e)
    t = threading.Thread(target=_delete, daemon=True)
    t.start()

def call_openrouter_chat(system: str, user_prompt: str, max_tokens=500):
    """
    Calls OpenRouter chat/completion. Uses the OpenAI-compatible endpoint.
    """
    url = "https://api.openrouter.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "deepseek/deepseek-r1:free",  # example free model; change as needed
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0
    }
    r = requests.post(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    data = r.json()
    # OpenRouter returns choices similar to OpenAI
    return data["choices"][0]["message"]["content"]

# -------------------------
# Routes
# -------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "RAG Backend API"}

@app.get("/upload", response_class=HTMLResponse)
def upload_form():
    return """
    <html><body>
      <h2>Upload PDF (RAG Demo)</h2>
      <form action="/upload" enctype="multipart/form-data" method="post">
        <input name="file" type="file" accept="application/pdf"/>
        <input type="submit"/>
      </form>
    </body></html>
    """

@app.post("/upload")
async def handle_upload(file: UploadFile = File(...)):
    sid = str(uuid.uuid4())[:8]
    save_path = UPLOAD_DIR / f"{sid}.pdf"
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Extract & chunk
    text = extract_text_from_pdf(save_path)
    if not text.strip():
        # schedule deletion quickly and error
        schedule_delete(sid, delay_seconds=30)
        return JSONResponse({"error": "No text could be extracted from the PDF."}, status_code=400)

    docs = text_splitter.split_text(text)
    # Create FAISS index (stored per-session directory)
    idx_dir = INDEX_DIR / sid
    idx_dir.mkdir(parents=True, exist_ok=True)
    # Build store
    store = FAISS.from_texts(docs, embedding=embeddings)
    # persist
    store.save_local(str(idx_dir))

    # schedule deletion after 5 minutes
    schedule_delete(sid, delay_seconds=300)

    # redirect to chat UI
    return RedirectResponse(url=f"/chat/{sid}", status_code=302)

@app.get("/chat/{session_id}", response_class=HTMLResponse)
def chat_page(session_id: str):
    return f"""
    <html><body>
      <h2>Chat with uploaded PDF — session {session_id}</h2>
      <div id="chat"></div>
      <input id="q" style="width:80%"/><button onclick="send()">Send</button>
      <script>
        async function send(){{
          const q = document.getElementById('q').value;
          const resp = await fetch('/api/chat/{session_id}', {{
            method:'POST',
            headers:{{'Content-Type':'application/json'}},
            body: JSON.stringify({{question:q}})
          }});
          const j = await resp.json();
          const div = document.getElementById('chat');
          div.innerHTML += '<div><b>You:</b> '+q+'</div><div><b>AI:</b> '+(j.answer||j.error)+'</div>';
          document.getElementById('q').value='';
        }}
      </script>
    </body></html>
    """

@app.post("/api/chat/{session_id}")
def api_chat(session_id: str, payload: dict):
    question = payload.get("question", "").strip()
    if not question:
        return JSONResponse({"error":"Empty question"}, status_code=400)

    # load FAISS store
    idx_dir = INDEX_DIR / session_id
    if not idx_dir.exists():
        return JSONResponse({"error":"Session index not found or expired"}, status_code=404)
    try:
        store = FAISS.load_local(str(idx_dir), embeddings)
    except Exception as e:
        return JSONResponse({"error": f"Failed loading index: {e}"}, status_code=500)

    docs = store.similarity_search(question, k=4)
    context_text = "\n\n---\n\n".join(d.page_content for d in docs)

    # Build prompt
    system = "You are a helpful assistant that answers user questions using ONLY the provided document excerpts. If the answer is not in the document, say 'Not Possible'. Be concise and include source snippets."
    user_prompt = f"Context:\n{context_text}\n\nUser question: {question}\nAnswer concisely, cite relevant snippet if useful."

    try:
        answer = call_openrouter_chat(system, user_prompt, max_tokens=400)
    except Exception as e:
        return JSONResponse({"error": f"OpenRouter call failed: {e}"}, status_code=500)

    return {"answer": answer}

# -------------------------
# main
# -------------------------
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
