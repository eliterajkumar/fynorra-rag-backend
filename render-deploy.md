# Render Deployment Guide

This guide covers deploying Fynorra RAG Backend to Render.

## Services Required

1. **Web Service** - Flask API
2. **Worker Service** - Celery worker
3. **PostgreSQL** - Database (or use Supabase)
4. **Redis** - Task queue broker

## Environment Variables

Set these in Render dashboard:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
DATABASE_URL=postgresql://user:password@host:5432/dbname
REDIS_URL=redis://redis-host:6379/0
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENV=us-east-1
PINECONE_INDEX=fynorra-dev-1
FYNORRA_API_KEY=your-fynorra-api-key
FYNORRA_EMBEDDING_URL=https://api.fynorra.com/v1/embeddings
FYNORRA_LLM_URL=https://api.fynorra.com/v1/chat/completions
MASTER_KEY=your-fernet-key
ADMIN_TOKEN=your-admin-token
ENV=production
SECRET_KEY=your-flask-secret-key
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K=5
MAX_TOKENS=1000
```

## Web Service Setup

1. **Create Web Service**
   - Connect GitHub repository
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn -w 4 -b 0.0.0.0:$PORT wsgi:app`
   - Health Check Path: `/health`

2. **Environment**
   - Python 3.11
   - Add all environment variables above

## Worker Service Setup

1. **Create Background Worker**
   - Same repository
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `celery -A src.tasks.celery_app worker --loglevel=info`
   - No health check needed

2. **Environment**
   - Same environment variables as Web Service

## Database Setup

Option 1: Use Supabase Postgres (recommended)
- Use your Supabase connection string for `DATABASE_URL`

Option 2: Render PostgreSQL
- Create PostgreSQL database
- Use connection string for `DATABASE_URL`

## Redis Setup

1. **Create Redis Instance**
   - Use Render Redis service or external provider (Upstash, etc.)
   - Set `REDIS_URL` in environment variables

## Initialization

After deployment, initialize the database:

```bash
# SSH into Render or use Render Shell
python migrations/0001_create_tables.py
```

Or via CLI:
```bash
python src/cli.py init-db
```

## Monitoring

- Check Render logs for errors
- Monitor Celery worker logs
- Use `/health` endpoint for health checks
- Consider adding Sentry (`SENTRY_DSN`) for error tracking

## Scaling

- Increase `-w` workers in gunicorn command for more API workers
- Add multiple Celery worker services for parallel ingestion
- Scale Redis and Postgres as needed

## Troubleshooting

1. **Worker not processing tasks**: Check Redis connection
2. **Database errors**: Verify `DATABASE_URL` format
3. **Auth failures**: Check `SUPABASE_JWT_SECRET` matches Supabase
4. **Pinecone errors**: Verify API key and index name

