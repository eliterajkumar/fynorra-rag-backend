#!/usr/bin/env python3
"""
Simple server runner for PDF Chatbot Platform
"""
import uvicorn
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from main import app

if __name__ == "__main__":
    print("🚀 Starting PDF Chatbot Platform...")
    print("📄 Upload PDFs at: http://localhost:8000/docs")
    print("💬 API Documentation: http://localhost:8000/docs")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=False,
        log_level="info"
    )