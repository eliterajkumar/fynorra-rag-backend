# document_processor.py
import os
from sentence_transformers import SentenceTransformer
import numpy as np
from supabase import create_client
import requests, json

# Supabase (uses same env vars as main.py)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "your_document_bucket")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# OpenRouter envs (use your provided names)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-oss-20b")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", 500))

# cached sentence-transformers model
_model = None
def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

# PDF extraction
def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        for p in doc:
            pages.append(p.get_text())
        return "\n".join(pages)
    except Exception:
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return file_bytes.decode("latin1", errors="ignore")

# chunker
def chunk_text(content: str, size: int = 800, overlap: int = 100):
    if not content:
        return []
    chunks = []
    step = max(1, size - overlap)
    for i in range(0, len(content), step):
        c = content[i:i+size].strip()
        if c:
            chunks.append(c)
    return chunks

# embeddings (returns numpy array)
def generate_embeddings(chunks):
    model = get_model()
    embs = model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)
    return embs

# save to Supabase messages table
def save_chunks_to_supabase(project_name, user_id, filename, chunks, embeddings, batch_size: int = 50):
    rows = []
    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        rows.append({
            "project": project_name,
            "role": "document",
            "content": chunk,
            "embedding": emb.tolist() if hasattr(emb, "tolist") else emb,
            "filename": filename,
            "user_id": user_id,
            "chunk_index": idx
        })
        if len(rows) >= batch_size:
            supabase.table("messages").insert(rows).execute()
            rows = []
    if rows:
        supabase.table("messages").insert(rows).execute()

# retrieval: cosine similarity over stored embeddings (JSON)
def retrieve_relevant_chunks(project_name: str, question: str, top_k: int = 5):
    resp = supabase.table("messages").select("content, embedding").eq("project", project_name).execute()
    rows = resp.data or []
    if not rows:
        return []
    
    model = get_model()
    q_emb = model.encode([question], convert_to_numpy=True)[0]
    sims = []
    
    for r in rows:
        emb = r.get("embedding") or []
        if not emb:
            continue
        try:
            emb_arr = np.array(emb, dtype=float)
        except Exception:
            continue
        denom = (np.linalg.norm(q_emb) * np.linalg.norm(emb_arr))
        if denom == 0:
            continue
        sim = float(np.dot(q_emb, emb_arr) / denom)
        sims.append((sim, r.get("content", "")))
    
    sims.sort(reverse=True, key=lambda x: x[0])
    return [text for _, text in sims[:top_k]]

# call OpenRouter chat completions
def call_openrouter_chat(messages, max_tokens: int = None):
    if max_tokens is None:
        max_tokens = MAX_TOKENS
    if not OPENROUTER_API_KEY:
        return None, "OpenRouter API key not configured"
    url = OPENROUTER_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if resp.status_code != 200:
            return None, f"OpenRouter API responded {resp.status_code}: {resp.text}"
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return None, "No choices from OpenRouter"
        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""
        return content, None
    except Exception as e:
        return None, str(e)

# high-level QA pipeline
def answer_question_with_context(project_name: str, question: str, top_k: int = 5):
    chunks = retrieve_relevant_chunks(project_name, question, top_k=top_k)
    if not chunks:
        return None, "No document chunks found for this project."
    
    system_prompt = (
        "You are a helpful assistant. Use the provided document context to answer succinctly. "
        "If the answer is not in the context, say you don't know."
    )
    messages = [{"role": "system", "content": system_prompt}]
    for idx, c in enumerate(chunks):
        messages.append({"role": "system", "content": f"Context {idx+1}: {c}"})
    messages.append({"role": "user", "content": question})
    
    answer, call_err = call_openrouter_chat(messages)
    if call_err:
        return None, f"LLM error: {call_err}"
    return answer, None
