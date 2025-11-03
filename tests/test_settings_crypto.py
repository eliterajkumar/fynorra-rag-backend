"""Tests for settings and crypto."""
import pytest
from src.security.crypto import encrypt_api_key, decrypt_api_key
from cryptography.fernet import Fernet
import base64
import os


def test_encrypt_decrypt_api_key():
    """Test encryption and decryption of API keys."""
    # Generate a test master key
    test_key = Fernet.generate_key().decode()
    os.environ["MASTER_KEY"] = test_key
    
    from src.config import Config
    Config.MASTER_KEY = test_key
    
    api_key = "test-api-key-12345"
    encrypted = encrypt_api_key(api_key)
    
    assert encrypted != api_key
    assert len(encrypted) > 0
    
    decrypted = decrypt_api_key(encrypted)
    assert decrypted == api_key


def test_encrypt_empty_key():
    """Test encrypting empty key."""
    test_key = Fernet.generate_key().decode()
    os.environ["MASTER_KEY"] = test_key
    
    from src.config import Config
    Config.MASTER_KEY = test_key
    
    encrypted = encrypt_api_key("")
    assert encrypted == ""


def test_settings_endpoint_structure():
    """Test settings endpoint structure."""
    from src.api.settings import settings_bp
    assert settings_bp is not None

