# Pinecone Integrated Embeddings Refactor - Summary

## Overview
Refactored the Fynorra RAG Backend to use Pinecone's integrated embeddings (server-side) instead of client-side embedding generation via Fynorra API.

## Changes Made

### 1. Configuration (`src/config.py`)
- ✅ Added `MAX_UPLOAD_BYTES` (20MB default)
- ✅ Added `BATCH_SIZE` (64 default) for Pinecone upserts
- ✅ Added `SUPABASE_BUCKET` config constant

### 2. Extractor (`src/ingest/extractor.py`)
- ✅ Changed `extract_text_from_pdf_bytes()` to return `List[str]` (one per page)
- ✅ Updated `extract_text_from_html()` to return `List[str]` (sections)
- ✅ Updated `extract_text_from_url()` to return `List[str]` of sections
- ✅ Added PyMuPDF (fitz) support for faster PDF extraction with fallback to pdfplumber

### 3. Chunker (`src/ingest/chunker.py`)
- ✅ Added `chunk_pages()` method to handle `List[str]` input (page-aware chunking)
- ✅ Returns chunks with page numbers preserved

### 4. Pinecone Client (`src/embeddings/pinecone_client.py`)
- ✅ Added `upsert_texts()` method - sends text to Pinecone, embeds server-side
- ✅ Added `query_text()` method - queries with text, Pinecone embeds server-side
- ✅ Added retry logic with exponential backoff for 429/5xx errors
- ✅ Kept legacy `upsert_vectors()` and `query_vectors()` for backward compatibility

**Note:** The Pinecone REST API URL format may need adjustment based on your actual Pinecone setup. The implementation uses `{index-name}.svc.pinecone.io` format, but serverless indexes may use a different format with project ID.

### 5. Worker (`src/tasks/worker_upsert_pinecone.py`)
- ✅ **NEW FILE** - Main worker using Pinecone integrated embeddings
- ✅ Removed all `EmbeddingAdapter` usage (no client-side embeddings)
- ✅ Uses `extract_text_from_pdf_bytes()` to get page list
- ✅ Uses `chunk_pages()` for page-aware chunking
- ✅ Builds records with `text` field (not `values`)
- ✅ Calls `pinecone_client.upsert_texts()` with namespace per user
- ✅ Handles both file uploads and URL scraping
- ✅ Implements retry logic with exponential backoff

### 6. Upload Endpoint (`src/api/ingest.py`)
- ✅ Enforces `MAX_UPLOAD_BYTES` file size limit
- ✅ Updated to use new `process_doc` worker task
- ✅ Scrape route already exists and updated

### 7. Query Endpoint (`src/api/query.py`)
- ✅ Removed `EmbeddingAdapter` import and usage
- ✅ Uses `pinecone_client.query_text()` instead of generating embeddings client-side
- ✅ Queries using text directly (Pinecone embeds server-side)
- ✅ Updated metadata field names (`doc_id`, `preview`)

### 8. Storage (`src/storage/supabase_storage.py`)
- ✅ Uses `Config.SUPABASE_BUCKET` instead of hardcoded bucket name

### 9. Celery Config (`src/tasks/celery_app.py`)
- ✅ Added new worker module to includes list

## Breaking Changes

1. **Worker Task Name Changed:**
   - Old: `ingest.upload_file`, `ingest.scrape_url`
   - New: `ingest.process_doc`
   - Update any external systems that reference task names

2. **Pinecone Integration:**
   - Requires Pinecone index configured for integrated embeddings
   - May need to adjust Pinecone API URL format based on your setup
   - Old vectors (client-side embeddings) won't be compatible with new text-based queries

3. **Metadata Fields:**
   - Query endpoint now expects `doc_id` instead of `document_id` in metadata
   - Uses `preview` field from metadata for context building

## Migration Notes

1. **Existing Vectors:** Old vectors created with client-side embeddings will need to be re-indexed using the new worker.

2. **Pinecone Setup:** Ensure your Pinecone index supports integrated embeddings. You may need to:
   - Configure the index with an embedding model (e.g., e5)
   - Verify the data-plane API URL format matches your setup

3. **Testing Required:**
   - Test upload endpoint with file size limits
   - Test worker with actual Pinecone index
   - Verify text-based upsert/queries work correctly
   - Test retry logic with rate limiting

## Next Steps

1. **Verify Pinecone API Format:**
   - Check if your Pinecone index uses integrated embeddings
   - Adjust `base_url` construction in `PineconeClient` if needed
   - Test upsert/queries with actual Pinecone instance

2. **Update Tests:**
   - Add tests for extractor returning page list
   - Add tests for worker with mocked Pinecone client
   - Add tests for query endpoint with text-based queries

3. **Deployment:**
   - Deploy to staging
   - Run smoke tests with sample documents
   - Verify Pinecone contains records with text fields
   - Validate query returns correct results

## Files Modified
- `src/config.py`
- `src/ingest/extractor.py`
- `src/ingest/chunker.py`
- `src/embeddings/pinecone_client.py`
- `src/storage/supabase_storage.py`
- `src/api/ingest.py`
- `src/api/query.py`
- `src/tasks/celery_app.py`

## Files Created
- `src/tasks/worker_upsert_pinecone.py`

## Files to Update Later
- `src/admin/reindex.py` - Should also use text-based upserts
- Tests - Need updates for new extraction/chunking approach

