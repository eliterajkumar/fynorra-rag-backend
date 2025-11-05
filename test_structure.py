#!/usr/bin/env python3
"""Minimal test script to verify code structure."""

import sys
import os
sys.path.append('/home/haxck/fynorra-rag-backend')

def test_imports():
    """Test basic Python imports."""
    try:
        # Test config
        from src.config import Config
        print("✅ Config module imports")
        
        # Test that config has required attributes
        attrs = ['SUPABASE_URL', 'DATABASE_URL', 'PINECONE_API_KEY', 'OPENAI_API_KEY']
        for attr in attrs:
            if hasattr(Config, attr):
                print(f"✅ Config.{attr} exists")
            else:
                print(f"❌ Config.{attr} missing")
                
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_file_structure():
    """Test file structure."""
    required_files = [
        'src/app.py',
        'src/config.py', 
        'src/api/ingest.py',
        'src/api/query.py',
        'src/tasks/worker_upsert_pinecone.py',
        'src/db/models.py',
        'requirements.txt',
        '.env'
    ]
    
    missing = []
    for file in required_files:
        if os.path.exists(f'/home/haxck/fynorra-rag-backend/{file}'):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} missing")
            missing.append(file)
    
    return len(missing) == 0

def test_env_file():
    """Test .env file has required variables."""
    env_path = '/home/haxck/fynorra-rag-backend/.env'
    if not os.path.exists(env_path):
        print("❌ .env file missing")
        return False
        
    with open(env_path, 'r') as f:
        content = f.read()
    
    required_vars = [
        'DATABASE_URL',
        'SUPABASE_URL', 
        'PINECONE_API_KEY',
        'OPENROUTER_API_KEY',
        'MASTER_KEY'
    ]
    
    missing = []
    for var in required_vars:
        if f'{var}=' in content:
            print(f"✅ {var} in .env")
        else:
            print(f"❌ {var} missing from .env")
            missing.append(var)
    
    return len(missing) == 0

def main():
    """Run basic structure tests."""
    print("🔍 Testing Fynorra RAG Backend Structure...\n")
    
    tests = [
        ("File Structure", test_file_structure),
        ("Environment Variables", test_env_file),
        ("Python Imports", test_imports)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        result = test_func()
        results.append(result)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Structure Tests: {passed}/{total} passed")
    
    if passed == total:
        print("✅ Code structure is correct!")
        print("\n🚀 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Start Redis: redis-server")
        print("3. Run migrations: python3 migrations/0001_create_tables.py")
        print("4. Start app: python3 src/app.py")
        print("5. Start worker: celery -A src.tasks.celery_app worker")
    else:
        print("❌ Fix structure issues first")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())