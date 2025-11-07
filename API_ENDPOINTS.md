# 🔗 API Endpoints

## Base URL
```
http://localhost:5000
```

## 📤 Upload Endpoints

### Upload PDF
```http
POST /upload_pdf
Content-Type: multipart/form-data
Authorization: Bearer <supabase_jwt_token>

Body: file (PDF file)
```

**Response:**
```json
{
  "success": true,
  "message": "PDF uploaded successfully",
  "document_id": "doc_123",
  "job_id": "job_456",
  "status": "processing"
}
```

### Check Upload Status
```http
GET /upload_pdf/status/<job_id>
Authorization: Bearer <supabase_jwt_token>
```

## 📊 Dataset Endpoints

### Get All Datasets
```http
GET /datasets
Authorization: Bearer <supabase_jwt_token>
```

**Response:**
```json
{
  "datasets": [
    {
      "id": "doc_123",
      "title": "document.pdf",
      "source_type": "upload",
      "status": "completed",
      "chunk_count": 25,
      "created_at": "2024-11-06T09:00:00Z"
    }
  ],
  "total": 1
}
```

### Delete Dataset
```http
DELETE /datasets/<dataset_id>
Authorization: Bearer <supabase_jwt_token>
```

## 💬 Query Endpoints

### Query Documents
```http
POST /api/query
Content-Type: application/json
Authorization: Bearer <supabase_jwt_token>

{
  "query": "What is the main topic?"
}
```

## 🧠 Brain Endpoints

### Get Documents
```http
GET /api/brain
Authorization: Bearer <supabase_jwt_token>
```

## 🔧 Test Endpoints

### Health Check
```http
GET /api/test
```

### Test Upload (No Auth)
```http
POST /api/test/upload
Content-Type: multipart/form-data

Body: file (any file)
```

## 🔐 Authentication

Use Supabase JWT token in Authorization header:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## ⚠️ CORS Enabled

All endpoints support CORS for frontend integration.