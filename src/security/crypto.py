"""Encryption utilities for API keys."""
from cryptography.fernet import Fernet
from src.config import Config
import base64


def get_cipher() -> Fernet:
    """Get Fernet cipher instance using MASTER_KEY."""
    if not Config.MASTER_KEY:
        raise ValueError("MASTER_KEY not configured")
    
    # Ensure key is 32 bytes base64-encoded
    key = Config.MASTER_KEY.encode()
    if len(key) != 44:  # Fernet key is base64-encoded 32 bytes = 44 chars
        # Derive key if not proper format
        key_bytes = key[:32] if len(key) >= 32 else key.ljust(32, b'0')
        key = base64.urlsafe_b64encode(key_bytes)
    
    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key using MASTER_KEY."""
    if not api_key:
        return ""
    
    cipher = get_cipher()
    encrypted = cipher.encrypt(api_key.encode())
    return encrypted.decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an encrypted API key."""
    if not encrypted_key:
        return ""
    
    cipher = get_cipher()
    decrypted = cipher.decrypt(encrypted_key.encode())
    return decrypted.decode()

