# 🚀 Deployment Guide

## Architecture Overview

```
Frontend → Main App (Port 5000) → Worker Service (Port 5001) → Background Processing
```

## Services

### 1. Main App (Lightweight)
- **Port**: 5000
- **Purpose**: API endpoints, authentication, file upload
- **Resources**: Low CPU, Low RAM

### 2. Worker Service (Heavy Processing)
- **Port**: 5001 (API) + Background Worker
- **Purpose**: Document processing, embeddings, vector storage
- **Resources**: High CPU, High RAM, GPU optional

## Deployment Options

### Option 1: Same Server
```bash
# Terminal 1 - Main App
cd main-app
python app.py

# Terminal 2 - Worker Service
cd data-ingestion
./start_services.sh
```

### Option 2: Separate Servers

**Server 1 (Main App):**
```bash
cd main-app
export WORKER_API_URL=http://worker-server:5001
python app.py
```

**Server 2 (Worker Service):**
```bash
cd data-ingestion
./start_services.sh
```

### Option 3: Docker Deployment

**Main App:**
```bash
cd main-app
docker-compose up
```

**Worker Service:**
```bash
cd data-ingestion
docker-compose up
```

## Environment Variables

### Main App (.env)
```
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
WORKER_API_URL=http://localhost:5001  # Change for remote worker
```

### Worker Service (.env)
```
DATABASE_URL=postgresql://...  # Same as main app
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk-...
```

## Communication Methods

1. **HTTP API** (Primary): Main app → Worker API
2. **Redis Queue** (Fallback): Async job queuing
3. **Database Polling** (Backup): Worker checks DB for jobs

## Scaling

- **Main App**: Scale horizontally (multiple instances)
- **Worker Service**: Scale vertically (more CPU/RAM) or horizontally (more workers)

## Monitoring

- Main App: `GET /api/test` - Health check
- Worker Service: `GET :5001/health` - Worker health
- Redis: Monitor queue length
- Database: Monitor job status

## Frontend Integration

Use Main App URL for all API calls:
```javascript
const API_BASE = 'http://your-main-app:5000'
```

Worker service is internal - frontend never calls it directly.