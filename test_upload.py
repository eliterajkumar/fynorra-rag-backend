#!/usr/bin/env python3
"""Quick test script for PDF upload without auth."""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_health():
    """Test health endpoint."""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health: {response.status_code} - {response.json()}")
    return response.status_code == 200

def test_upload_no_auth():
    """Test upload without auth (modify API temporarily)."""
    # Create test file
    with open("test.txt", "w") as f:
        f.write("This is a test document for the RAG system. It contains sample text for testing.")
    
    # Upload file
    with open("test.txt", "rb") as f:
        files = {"file": ("test.txt", f, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/upload", files=files)
    
    print(f"Upload: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Job ID: {data.get('jobId')}")
        return data.get('jobId')
    else:
        print(f"Error: {response.text}")
        return None

if __name__ == "__main__":
    print("🧪 Testing Fynorra RAG Backend...")
    
    if test_health():
        print("✅ Health check passed")
        job_id = test_upload_no_auth()
        if job_id:
            print("✅ Upload test passed")
        else:
            print("❌ Upload test failed")
    else:
        print("❌ Health check failed - is the server running?")