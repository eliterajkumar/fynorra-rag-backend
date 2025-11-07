# 🔓 No-Auth API Endpoints (Development Only)

## Base URL
```
http://localhost:5000/api/dev
```

## 📤 Upload & Processing

### **Upload File**
```http
POST /api/dev/upload
Content-Type: multipart/form-data

Body: file (PDF, TXT, HTML)
```

**Response:**
```json
{
  "jobId": "job_123",
  "documentId": "doc_456",
  "status": "queued"
}
```

### **Scrape URL**
```http
POST /api/dev/scrape
Content-Type: application/json

{
  "url": "https://example.com/article"
}
```

### **Check Upload Status**
```http
GET /api/dev/upload/status?jobId=job_123
```

**Response:**
```json
{
  "jobId": "job_123",
  "status": "completed",
  "progress": 100,
  "errorMessage": null
}
```

## 🧠 Documents Management

### **Get All Documents**
```http
GET /api/dev/brain?limit=20&offset=0
```

**Response:**
```json
{
  "documents": [
    {
      "id": "doc_123",
      "title": "document.pdf",
      "sourceType": "upload",
      "fileType": "pdf",
      "chunkCount": 25,
      "status": "completed",
      "createdAt": "2024-11-06T09:00:00Z"
    }
  ],
  "totalDocuments": 5,
  "totalChunks": 125,
  "limit": 20,
  "offset": 0
}
```

## 💬 Chat Interface

### **Query Documents**
```http
POST /api/dev/query
Content-Type: application/json

{
  "query": "What is the main topic?",
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "Based on the documents, the main topic is...",
  "sources": [
    {
      "documentId": "doc_123",
      "title": "document.pdf",
      "score": 0.95,
      "chunkIndex": 2,
      "pageNumber": 1
    }
  ],
  "tokensUsed": 150
}
```

## 🎯 Frontend Integration

### **Upload Page**
```javascript
const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('http://localhost:5000/api/dev/upload', {
    method: 'POST',
    body: formData
  });
  
  return response.json();
};
```

### **Documents List**
```javascript
const getDocuments = async () => {
  const response = await fetch('http://localhost:5000/api/dev/brain');
  return response.json();
};
```

### **Chat Interface**
```javascript
const queryDocuments = async (query) => {
  const response = await fetch('http://localhost:5000/api/dev/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query })
  });
  
  return response.json();
};
```

## ⚠️ Important Notes

- **Development Only** - These endpoints bypass authentication
- **Single User** - All data stored under dummy user `dev-user-123`
- **No Security** - Don't use in production
- **CORS Enabled** - Works with frontend

## 🔄 Switch to Production

When ready for production, change URLs from:
- `/api/dev/upload` → `/api/upload` (with auth)
- `/api/dev/brain` → `/api/brain` (with auth)
- `/api/dev/query` → `/api/query` (with auth)

And add Supabase authentication! 🔐