from cryptography.fernet import Fernet
from django.conf import settings
import base64
import os

def get_fernet():
    """Calculates a Fernet key based on SECRET_KEY for DB encryption."""
    # We use the SECRET_KEY to derive a valid 32-byte Fernet key
    # Ensure SECRET_KEY is long enough
    key = settings.SECRET_KEY[:32]
    if len(key) < 32:
        # Pad if too short (highly unlikely for Django generated keys)
        key = key.ljust(32, 'x')
    
    # Fernet requires a base64 encoded 32-byte key
    encoded_key = base64.urlsafe_b64encode(key.encode())
    return Fernet(encoded_key)

def encrypt_token(token: str) -> str:
    """Encrypts a token string."""
    if not token:
        return None
    f = get_fernet()
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypts an encrypted token string."""
    if not encrypted_token:
        return None
    f = get_fernet()
    try:
        return f.decrypt(encrypted_token.encode()).decode()
    except Exception:
        # Return None or handle invalid token
        return None
