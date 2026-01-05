"""
Digital Signature Service
Handles digital signature operations using AR CFM certificates
"""

import hashlib
import base64
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography import x509
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class DigitalSignatureService:
    """
    Service for handling digital signatures with AR CFM certificates
    
    Supports:
    - Document hashing (SHA-256)
    - Signature generation and verification
    - Certificate validation
    """
    
    @staticmethod
    def hash_document(document_content: bytes) -> str:
        """
        Generate SHA-256 hash of document content
        
        Args:
            document_content: Document bytes
            
        Returns:
            Hexadecimal hash string
        """
        hash_obj = hashlib.sha256(document_content)
        return hash_obj.hexdigest()
    
    @staticmethod
    def hash_document_string(document_content: str) -> str:
        """
        Generate SHA-256 hash of document string
        
        Args:
            document_content: Document string
            
        Returns:
            Hexadecimal hash string
        """
        return DigitalSignatureService.hash_document(document_content.encode('utf-8'))
    
    @staticmethod
    def verify_signature(
        document_hash: str,
        signature_data: str,
        public_key_pem: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify digital signature
        
        Args:
            document_hash: SHA-256 hash of the document
            signature_data: Base64 encoded signature
            public_key_pem: PEM formatted public key (optional, for verification)
            
        Returns:
            Dictionary with verification result
        """
        try:
            # Decode signature
            signature_bytes = base64.b64decode(signature_data)
            
            # If public key provided, verify cryptographically
            if public_key_pem:
                try:
                    public_key = serialization.load_pem_public_key(
                        public_key_pem.encode('utf-8'),
                        backend=default_backend()
                    )
                    
                    # Verify signature
                    public_key.verify(
                        signature_bytes,
                        document_hash.encode('utf-8'),
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH
                        ),
                        hashes.SHA256()
                    )
                    
                    return {
                        'is_valid': True,
                        'message': 'Signature verified successfully'
                    }
                except Exception as e:
                    logger.warning(f"Signature verification failed: {str(e)}")
                    return {
                        'is_valid': False,
                        'error': f'Signature verification failed: {str(e)}'
                    }
            else:
                # Basic validation: check signature format
                if len(signature_bytes) > 0:
                    return {
                        'is_valid': True,
                        'message': 'Signature format valid (cryptographic verification requires public key)'
                    }
                else:
                    return {
                        'is_valid': False,
                        'error': 'Invalid signature format'
                    }
                    
        except Exception as e:
            logger.error(f"Error verifying signature: {str(e)}", exc_info=True)
            return {
                'is_valid': False,
                'error': f'Error verifying signature: {str(e)}'
            }
    
    @staticmethod
    def extract_certificate_info(certificate_pem: str) -> Dict[str, Any]:
        """
        Extract information from AR CFM certificate
        
        Args:
            certificate_pem: PEM formatted certificate
            
        Returns:
            Dictionary with certificate information
        """
        try:
            cert = x509.load_pem_x509_certificate(
                certificate_pem.encode('utf-8'),
                default_backend()
            )
            
            # Extract subject information
            subject = cert.subject
            issuer = cert.issuer
            
            # Try to extract CRM from subject
            crm_number = None
            crm_state = None
            
            for attr in subject:
                if attr.oid._name == 'commonName' or attr.oid._name == 'CN':
                    cn_value = attr.value
                    # Try to parse CRM from CN (format may vary)
                    # Example: "Dr. João Silva - CRM 123456/SP"
                    if 'CRM' in cn_value:
                        parts = cn_value.split('CRM')
                        if len(parts) > 1:
                            crm_part = parts[1].strip()
                            if '/' in crm_part:
                                crm_number, crm_state = crm_part.split('/')
                                crm_number = crm_number.strip()
                                crm_state = crm_state.strip()
            
            return {
                'serial_number': str(cert.serial_number),
                'issuer': issuer.rfc4514_string(),
                'subject': subject.rfc4514_string(),
                'valid_from': cert.not_valid_before,
                'valid_to': cert.not_valid_after,
                'crm_number': crm_number,
                'crm_state': crm_state,
                'is_valid': datetime.now() < cert.not_valid_after and datetime.now() > cert.not_valid_before
            }
        except Exception as e:
            logger.error(f"Error extracting certificate info: {str(e)}", exc_info=True)
            return {
                'error': f'Error extracting certificate info: {str(e)}'
            }
    
    @staticmethod
    def create_signature_data(
        document_hash: str,
        private_key_pem: Optional[str] = None
    ) -> str:
        """
        Create signature data from document hash
        
        Note: In production, this should use a hardware token or secure key storage.
        For now, this is a placeholder that would need to be implemented with actual
        certificate/key management.
        
        Args:
            document_hash: SHA-256 hash of the document
            private_key_pem: PEM formatted private key (optional, for testing)
            
        Returns:
            Base64 encoded signature
        """
        # This is a placeholder implementation
        # In production, you would:
        # 1. Load private key from secure storage or hardware token
        # 2. Sign the document hash
        # 3. Return base64 encoded signature
        
        if private_key_pem:
            try:
                private_key = serialization.load_pem_private_key(
                    private_key_pem.encode('utf-8'),
                    password=None,
                    backend=default_backend()
                )
                
                signature = private_key.sign(
                    document_hash.encode('utf-8'),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                
                return base64.b64encode(signature).decode('utf-8')
            except Exception as e:
                logger.error(f"Error creating signature: {str(e)}", exc_info=True)
                raise
        
        # For now, return a placeholder (in production, this should never happen)
        logger.warning("No private key provided - returning placeholder signature")
        placeholder = base64.b64encode(b"placeholder_signature").decode('utf-8')
        return placeholder
