#!/usr/bin/env python3
"""Simple test script to verify core functionality."""

import sys
import os
sys.path.append('/home/haxck/fynorra-rag-backend')

def test_config():
    """Test configuration loading."""
    try:
        from src.config import Config
        print("✅ Config loaded successfully")
        
        # Check required fields
        required = ['SUPABASE_URL', 'DATABASE_URL', 'PINECONE_API_KEY', 'MASTER_KEY']
        missing = []
        for field in required:
            if not getattr(Config, field):
                missing.append(field)
        
        if missing:
            print(f"❌ Missing config: {', '.join(missing)}")
            return False
        else:
            print("✅ All required config present")
            return True
            
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False

def test_database():
    """Test database connection."""
    try:
        from src.db.session import get_db_session
        db = get_db_session()
        db.execute("SELECT 1")
        db.close()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_pinecone():
    """Test Pinecone connection."""
    try:
        from src.embeddings.pinecone_client import PineconeClient
        pc = PineconeClient()
        # Just initialize, don't query
        print("✅ Pinecone client initialized")
        return True
    except Exception as e:
        print(f"❌ Pinecone error: {e}")
        return False

def test_flask_app():
    """Test Flask app creation."""
    try:
        from src.app import create_app
        app = create_app()
        print("✅ Flask app created successfully")
        return True
    except Exception as e:
        print(f"❌ Flask app error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running Fynorra RAG Backend Tests...\n")
    
    tests = [
        ("Configuration", test_config),
        ("Database", test_database), 
        ("Pinecone", test_pinecone),
        ("Flask App", test_flask_app)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"Testing {name}...")
        result = test_func()
        results.append(result)
        print()
    
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Ready to run.")
        return 0
    else:
        print("❌ Some tests failed. Check configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())