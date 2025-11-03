# Fynorra RAG Backend

Production-ready Flask backend for a Retrieval-Augmented Generation (RAG) AI system.

## Features

- **Document Ingestion**: Upload files (PDF, HTML, TXT) or scrape URLs
- **Vector Storage**: Pinecone integration for semantic search
- **RAG Pipeline**: Query documents with AI-powered answers and citations
- **Async Processing**: Celery workers for background ingestion tasks
- **Authentication**: Supabase JWT-based auth
- **Custom LLMs**: Support for user-provided API keys (encrypted)
- **Admin Tools**: Reindexing and garbage collection

## Tech Stack

- **Python 3.11**
- **Flask** - REST API framework
- **SQLAlchemy** - Database ORM
- **Celery + Redis** - Async task queue
- **Supabase** - Auth, Postgres, Storage
- **Pinecone** - Vector database
- **Fynorra** - Default LLM & Embeddings API

## Project Structure

```
fynorra-rag-backend/
├── src/
│   ├── app.py                 # Flask app factory
│   ├── config.py              # Configuration management
│   ├── cli.py                 # CLI commands
│   ├── auth/                  # Supabase authentication
│   ├── api/                   # REST API endpoints
│   ├── db/                    # Database models & session
│   ├── ingest/                # Text extraction & chunking
│   ├── embeddings/            # Embedding providers & Pinecone
│   ├── llm/                   # LLM provider adapters
│   ├── tasks/                 # Celery async tasks
│   ├── security/              # Encryption utilities
│   ├── storage/               # Supabase Storage helper
│   └── admin/                 # Admin endpoints
├── tests/                     # Unit tests
├── migrations/                # Database migrations
└── requirements.txt           # Python dependencies
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`
- `DATABASE_URL` (Supabase Postgres connection string)
- `REDIS_URL`
- `PINECONE_API_KEY`, `PINECONE_INDEX`
- `FYNORRA_API_KEY`
- `MASTER_KEY` (generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)

### 3. Initialize Database

```bash
python src/cli.py init-db
```

Or run the migration:

```bash
python migrations/0001_create_tables.py
```

### 4. Run Locally

**Start Redis**:
```bash
redis-server
```

**Start Celery Worker** (in separate terminal):
```bash
celery -A src.tasks.celery_app worker --loglevel=info
```

**Start Flask App**:
```bash
python src/app.py
```

Or use Docker Compose:
```bash
docker-compose up
```

## API Endpoints

### Ingestion

- `POST /api/upload` - Upload file, enqueue ingestion
- `POST /api/scrape` - Scrape URL, enqueue ingestion
- `GET /api/upload/status?jobId=...` - Check ingestion progress

### Brain (Documents)

- `GET /api/brain` - List user documents and stats
- `GET /api/brain/<docId>/vectors` - Preview chunks for a document

### Query

- `POST /api/query` - Query RAG system, get AI answer with citations
  ```json
  {
    "query": "What is the main topic?",
    "top_k": 5
  }
  ```

### Settings

- `GET /api/user/settings` - Get user settings
- `POST /api/user/settings` - Update settings (encrypt API keys)
  ```json
  {
    "customLLMAPIKey": "sk-...",
    "preferredLLMProvider": "openai"
  }
  ```

### Admin

- `POST /api/admin/reindex` - Reindex vectors (requires `ADMIN_TOKEN`)
- `POST /api/admin/garbage-collect` - Clean up orphaned vectors

## Authentication

All endpoints (except `/health`) require a Supabase JWT token:

```
Authorization: Bearer <supabase-jwt-token>
```

## Testing

Run tests with pytest:

```bash
pytest tests/
```

## Deployment

See [render-deploy.md](render-deploy.md) for Render deployment instructions.

## License

MIT

