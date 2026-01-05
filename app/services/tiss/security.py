"""
TISS Security Service
Handles encryption, digital signatures, and data protection
"""

import logging
import hashlib
import base64
from typing import Optional, Dict
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import os

logger = logging.getLogger(__name__)


class TISSSecurityService:
    """Service for TISS security operations"""
    
    def __init__(self, private_key_path: Optional[str] = None, public_key_path: Optional[str] = None):
        """
        Initialize security service
        
        Args:
            private_key_path: Path to private key file (PEM format)
            public_key_path: Path to public key file (PEM format)
        """
        self.private_key = None
        self.public_key = None
        
        # Load keys if paths provided
        if private_key_path and os.path.exists(private_key_path):
            with open(private_key_path, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
        
        if public_key_path and os.path.exists(public_key_path):
            with open(public_key_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
        
        # Get encryption key from environment
        encryption_key = os.getenv('TISS_ENCRYPTION_KEY')
        if encryption_key:
            try:
                self.encryption_key = base64.urlsafe_b64decode(encryption_key.encode())
            except Exception:
                # Generate new key if provided key is invalid
                self.encryption_key = Fernet.generate_key()
                logger.warning("Invalid TISS_ENCRYPTION_KEY, using generated key")
        else:
            self.encryption_key = Fernet.generate_key()
            logger.warning("TISS_ENCRYPTION_KEY not set, using generated key (not suitable for production)")
    
    def sign_data(self, data: bytes) -> str:
        """
        Create digital signature for data
        
        Args:
            data: Data to sign (bytes)
            
        Returns:
            Base64-encoded signature
        """
        if not self.private_key:
            raise ValueError("Private key not available for signing")
        
        try:
            signature = self.private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            logger.error(f"Error signing data: {e}")
            raise
    
    def verify_signature(self, data: bytes, signature: str) -> bool:
        """
        Verify digital signature
        
        Args:
            data: Original data (bytes)
            signature: Base64-encoded signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.public_key:
            raise ValueError("Public key not available for verification")
        
        try:
            signature_bytes = base64.b64decode(signature.encode('utf-8'))
            self.public_key.verify(
                signature_bytes,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    def encrypt_data(self, data: bytes) -> bytes:
        """
        Encrypt sensitive data at rest
        
        Args:
            data: Data to encrypt (bytes)
            
        Returns:
            Encrypted data (bytes)
        """
        try:
            fernet = Fernet(base64.urlsafe_b64encode(self.encryption_key).decode('utf-8'))
            return fernet.encrypt(data)
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data: Encrypted data (bytes)
            
        Returns:
            Decrypted data (bytes)
        """
        try:
            fernet = Fernet(base64.urlsafe_b64encode(self.encryption_key).decode('utf-8'))
            return fernet.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise
    
    def calculate_integrity_hash(self, data: bytes) -> str:
        """
        Calculate SHA-256 hash for data integrity
        
        Args:
            data: Data to hash (bytes)
            
        Returns:
            Hex-encoded hash
        """
        return hashlib.sha256(data).hexdigest()
    
    def verify_integrity(self, data: bytes, expected_hash: str) -> bool:
        """
        Verify data integrity using hash
        
        Args:
            data: Data to verify (bytes)
            expected_hash: Expected hash (hex-encoded)
            
        Returns:
            True if hash matches, False otherwise
        """
        actual_hash = self.calculate_integrity_hash(data)
        return actual_hash == expected_hash
    
    def encrypt_sensitive_fields(self, data: Dict, fields_to_encrypt: list) -> Dict:
        """
        Encrypt specific fields in a dictionary
        
        Args:
            data: Dictionary with data
            fields_to_encrypt: List of field names to encrypt
            
        Returns:
            Dictionary with encrypted fields (as base64 strings)
        """
        encrypted_data = data.copy()
        
        for field in fields_to_encrypt:
            if field in encrypted_data and encrypted_data[field]:
                value = encrypted_data[field]
                if isinstance(value, str):
                    value_bytes = value.encode('utf-8')
                elif isinstance(value, bytes):
                    value_bytes = value
                else:
                    import json
                    value_bytes = json.dumps(value).encode('utf-8')
                
                encrypted = self.encrypt_data(value_bytes)
                encrypted_data[field] = base64.b64encode(encrypted).decode('utf-8')
                encrypted_data[f'{field}_encrypted'] = True
        
        return encrypted_data
    
    def decrypt_sensitive_fields(self, data: Dict, fields_to_decrypt: list) -> Dict:
        """
        Decrypt specific fields in a dictionary
        
        Args:
            data: Dictionary with encrypted data
            fields_to_decrypt: List of field names to decrypt
            
        Returns:
            Dictionary with decrypted fields
        """
        decrypted_data = data.copy()
        
        for field in fields_to_decrypt:
            if field in decrypted_data and decrypted_data.get(f'{field}_encrypted'):
                encrypted_value = decrypted_data[field]
                encrypted_bytes = base64.b64decode(encrypted_value.encode('utf-8'))
                decrypted_bytes = self.decrypt_data(encrypted_bytes)
                
                # Try to decode as JSON, fallback to string
                try:
                    import json
                    decrypted_data[field] = json.loads(decrypted_bytes.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    decrypted_data[field] = decrypted_bytes.decode('utf-8')
                
                decrypted_data.pop(f'{field}_encrypted', None)
        
        return decrypted_data

