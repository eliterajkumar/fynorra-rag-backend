# Deployment Guide - Fynorra RAG Backend

## Quick Deploy Options

### 1. Render (Recommended - Easiest)

**Step 1: Create Services**
```bash
# 1. Fork/clone repo to GitHub
# 2. Create Render account
# 3. Create 4 services:
```

**Web Service:**
- Repository: `your-github/fynorra-rag-backend`
- Build: `pip install -r requirements.txt`
- Start: `gunicorn -w 4 -b 0.0.0.0:$PORT wsgi:app`
- Health Check: `/health`

**Worker Service:**
- Same repo
- Build: `pip install -r requirements.txt` 
- Start: `celery -A src.tasks.celery_app worker --loglevel=info`

**Redis:** Create Redis instance
**PostgreSQL:** Create PostgreSQL database (or use Supabase)

**Step 2: Environment Variables**
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_JWT_SECRET=your-jwt-secret
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX=fynorra-prod
OPENROUTER_API_KEY=your-openrouter-key
OPENAI_API_KEY=your-openai-key
MASTER_KEY=generate-with-fernet
ENV=production
```

**Step 3: Initialize**
```bash
# After deploy, run once:
python migrations/0001_create_tables.py
```

### 2. Railway

**Deploy Button:**
```bash
# 1. Click Railway deploy button (if configured)
# 2. Or connect GitHub repo manually
# 3. Add environment variables
# 4. Deploy web + worker services
```

**Services:**
- Web: `gunicorn wsgi:app`
- Worker: `celery -A src.tasks.celery_app worker`
- Redis: Railway Redis plugin
- Postgres: Railway PostgreSQL plugin

### 3. Heroku

**Step 1: Setup**
```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:mini
heroku addons:create heroku-redis:mini
```

**Step 2: Configure**
```bash
# Set environment variables
heroku config:set SUPABASE_URL=https://...
heroku config:set OPENROUTER_API_KEY=sk-...
# ... (all other env vars)
```

**Step 3: Deploy**
```bash
git push heroku main
heroku run python migrations/0001_create_tables.py
heroku ps:scale worker=1  # Scale worker dyno
```

### 4. DigitalOcean App Platform

**Step 1: Create App**
- Connect GitHub repository
- Configure components:

**Web Component:**
```yaml
name: api
source_dir: /
github:
  repo: your-username/fynorra-rag-backend
  branch: main
run_command: gunicorn -w 4 -b 0.0.0.0:$PORT wsgi:app
environment_slug: python
instance_count: 1
instance_size_slug: basic-xxs
```

**Worker Component:**
```yaml
name: worker
source_dir: /
run_command: celery -A src.tasks.celery_app worker --loglevel=info
instance_count: 1
instance_size_slug: basic-xxs
```

**Step 2: Add Databases**
- Add Redis cluster
- Add PostgreSQL database (or use Supabase)

### 5. AWS (Advanced)

**Using ECS + RDS + ElastiCache:**

**Step 1: Infrastructure**
```bash
# Create RDS PostgreSQL instance
# Create ElastiCache Redis cluster  
# Create ECS cluster
# Create Application Load Balancer
```

**Step 2: Docker Deploy**
```bash
# Build and push to ECR
docker build -t fynorra-rag .
aws ecr get-login-password | docker login --username AWS --password-stdin
docker tag fynorra-rag:latest your-account.dkr.ecr.region.amazonaws.com/fynorra-rag:latest
docker push your-account.dkr.ecr.region.amazonaws.com/fynorra-rag:latest
```

**Step 3: ECS Services**
- Web service: `gunicorn wsgi:app`
- Worker service: `celery worker`

### 6. Google Cloud Run

**Step 1: Build**
```bash
gcloud builds submit --tag gcr.io/PROJECT-ID/fynorra-rag
```

**Step 2: Deploy Web**
```bash
gcloud run deploy fynorra-api \
  --image gcr.io/PROJECT-ID/fynorra-rag \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="ENV=production,REDIS_URL=redis://..."
```

**Step 3: Deploy Worker**
```bash
gcloud run deploy fynorra-worker \
  --image gcr.io/PROJECT-ID/fynorra-rag \
  --platform managed \
  --region us-central1 \
  --no-allow-unauthenticated \
  --command="celery" \
  --args="-A,src.tasks.celery_app,worker,--loglevel=info"
```

## Required Environment Setup

### 1. Supabase Setup
```bash
# 1. Create Supabase project
# 2. Get credentials from Settings > API
# 3. Create storage bucket: "fynorra-documents"
# 4. Set RLS policies for user isolation
```

### 2. Pinecone Setup  
```bash
# 1. Create Pinecone account
# 2. Create index: dimension=1536, metric=cosine
# 3. Get API key from console
```

### 3. OpenRouter Setup
```bash
# 1. Create OpenRouter account  
# 2. Get free tier API key
# 3. Test with curl:
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "meta-llama/llama-3.2-3b-instruct:free", "messages": [{"role": "user", "content": "Hello"}]}'
```

### 4. Generate Master Key
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Post-Deployment Checklist

1. **Test Health Endpoint**
   ```bash
   curl https://your-app.com/health
   ```

2. **Initialize Database**
   ```bash
   python migrations/0001_create_tables.py
   ```

3. **Test Upload**
   ```bash
   curl -X POST https://your-app.com/api/upload \
     -H "Authorization: Bearer $SUPABASE_JWT" \
     -F "file=@test.pdf"
   ```

4. **Test Query**
   ```bash
   curl -X POST https://your-app.com/api/query \
     -H "Authorization: Bearer $SUPABASE_JWT" \
     -H "Content-Type: application/json" \
     -d '{"query": "What is this document about?"}'
   ```

5. **Monitor Logs**
   - Check web service logs
   - Check worker service logs  
   - Monitor Redis/Postgres connections

## Scaling Recommendations

**Small (< 100 users):**
- 1 web instance
- 1 worker instance
- Basic Redis/Postgres

**Medium (100-1000 users):**
- 2-3 web instances
- 2-3 worker instances  
- Redis cluster
- Postgres with read replicas

**Large (1000+ users):**
- Auto-scaling web instances
- Dedicated worker pools
- Redis cluster with failover
- Postgres with connection pooling
- CDN for static assets

## Cost Optimization

1. **Use free tiers:**
   - OpenRouter free tier (500 tokens)
   - Supabase free tier
   - Render free tier

2. **Optimize embeddings:**
   - Batch OpenAI API calls
   - Cache embeddings
   - Use smaller chunk sizes

3. **Monitor usage:**
   - Set up billing alerts
   - Track token usage
   - Monitor storage costs

## Troubleshooting

**Common Issues:**

1. **Worker not processing:** Check Redis connection
2. **Auth failures:** Verify JWT secret matches Supabase  
3. **Embedding errors:** Check OpenAI API key and quotas
4. **Pinecone errors:** Verify index name and dimensions
5. **File upload fails:** Check Supabase storage permissions

**Debug Commands:**
```bash
# Check Redis connection
redis-cli -u $REDIS_URL ping

# Test Celery
celery -A src.tasks.celery_app inspect active

# Check database
python -c "from src.db.session import get_db_session; print('DB OK')"
```