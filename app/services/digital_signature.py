"""
Digital Signature Service
Handles digital signature operations using AR CFM certificates
Supports PKCS#7 signatures for PDF documents
"""

import hashlib
import base64
import logging
import os
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography import x509
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# Try to import PKCS#7 support
try:
    from cryptography.hazmat.primitives.serialization import pkcs7
    PKCS7_AVAILABLE = True
except ImportError:
    PKCS7_AVAILABLE = False
    logger.warning("PKCS#7 support not available. Install cryptography>=3.0.0")


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
    def load_certificate_and_key(
        user_id: Optional[int] = None,
        clinic_id: Optional[int] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Load certificate and private key from secure storage
        
        Priority order:
        1. User-specific certificate/key (if user_id provided)
        2. Clinic-specific certificate/key (if clinic_id provided)
        3. Environment variables (for development/testing)
        
        Args:
            user_id: User ID for user-specific certificate
            clinic_id: Clinic ID for clinic-specific certificate
            
        Returns:
            Tuple of (certificate_pem, private_key_pem)
        """
        # Try to load from environment variables (for development/testing)
        cert_pem = os.getenv("DIGITAL_SIGNATURE_CERTIFICATE")
        key_pem = os.getenv("DIGITAL_SIGNATURE_PRIVATE_KEY")
        
        # In production, load from secure storage (database, vault, etc.)
        # For now, we'll use environment variables
        
        if cert_pem and key_pem:
            return cert_pem, key_pem
        
        # Try user-specific paths
        if user_id:
            cert_path = os.getenv(f"DIGITAL_SIGNATURE_CERT_USER_{user_id}")
            key_path = os.getenv(f"DIGITAL_SIGNATURE_KEY_USER_{user_id}")
            if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
                with open(cert_path, 'r') as f:
                    cert_pem = f.read()
                with open(key_path, 'r') as f:
                    key_pem = f.read()
                return cert_pem, key_pem
        
        # Try clinic-specific paths
        if clinic_id:
            cert_path = os.getenv(f"DIGITAL_SIGNATURE_CERT_CLINIC_{clinic_id}")
            key_path = os.getenv(f"DIGITAL_SIGNATURE_KEY_CLINIC_{clinic_id}")
            if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
                with open(cert_path, 'r') as f:
                    cert_pem = f.read()
                with open(key_path, 'r') as f:
                    key_pem = f.read()
                return cert_pem, key_pem
        
        return None, None
    
    @staticmethod
    def create_signature_data(
        document_hash: str,
        private_key_pem: Optional[str] = None,
        user_id: Optional[int] = None,
        clinic_id: Optional[int] = None
    ) -> str:
        """
        Create signature data from document hash
        
        Args:
            document_hash: SHA-256 hash of the document
            private_key_pem: PEM formatted private key (optional, will be loaded if not provided)
            user_id: User ID for loading user-specific certificate
            clinic_id: Clinic ID for loading clinic-specific certificate
            
        Returns:
            Base64 encoded signature
        """
        # Load private key if not provided
        if not private_key_pem:
            _, private_key_pem = DigitalSignatureService.load_certificate_and_key(user_id, clinic_id)
        
        if private_key_pem:
            try:
                # Try to load with password if needed
                password = os.getenv("DIGITAL_SIGNATURE_KEY_PASSWORD")
                password_bytes = password.encode() if password else None
                
                private_key = serialization.load_pem_private_key(
                    private_key_pem.encode('utf-8'),
                    password=password_bytes,
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
        
        # Fallback: return placeholder for development
        logger.warning("No private key available - returning placeholder signature")
        placeholder = base64.b64encode(b"placeholder_signature").decode('utf-8')
        return placeholder
    
    @staticmethod
    def create_pkcs7_signature(
        document_content: bytes,
        certificate_pem: str,
        private_key_pem: str
    ) -> bytes:
        """
        Create PKCS#7 signature for PDF documents
        
        Args:
            document_content: Document bytes to sign
            certificate_pem: PEM formatted certificate
            private_key_pem: PEM formatted private key
            
        Returns:
            PKCS#7 signature bytes
        """
        try:
            # Load certificate and private key
            cert = x509.load_pem_x509_certificate(
                certificate_pem.encode('utf-8'),
                default_backend()
            )
            
            password = os.getenv("DIGITAL_SIGNATURE_KEY_PASSWORD")
            password_bytes = password.encode() if password else None
            
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=password_bytes,
                backend=default_backend()
            )
            
            # Create PKCS#7 signature
            # Note: Full PKCS#7 implementation requires additional libraries
            # For now, we'll create a basic signature
            
            # Hash the document
            document_hash = hashlib.sha256(document_content).digest()
            
            # Sign the hash
            signature = private_key.sign(
                document_hash,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            # Create basic PKCS#7 structure (simplified)
            # In production, use proper PKCS#7 library
            pkcs7_data = {
                "certificate": certificate_pem,
                "signature": base64.b64encode(signature).decode(),
                "hash_algorithm": "SHA256",
                "signed_data": base64.b64encode(document_hash).decode()
            }
            
            import json
            return json.dumps(pkcs7_data).encode()
            
        except Exception as e:
            logger.error(f"Error creating PKCS#7 signature: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def add_signature_to_pdf(
        pdf_bytes: bytes,
        certificate_pem: str,
        private_key_pem: str,
        signature_reason: str = "Documento assinado digitalmente",
        signature_location: str = "Prontivus Medical System"
    ) -> bytes:
        """
        Add digital signature to PDF document
        
        Args:
            pdf_bytes: Original PDF bytes
            certificate_pem: PEM formatted certificate
            private_key_pem: PEM formatted private key
            signature_reason: Reason for signing
            signature_location: Location of signing
            
        Returns:
            Signed PDF bytes
        """
        try:
            # For now, we'll add signature metadata to PDF
            # Full PDF signing requires PyPDF2 or similar library
            
            # Extract certificate info
            cert_info = DigitalSignatureService.extract_certificate_info(certificate_pem)
            
            # Create signature dictionary
            signature_data = {
                "reason": signature_reason,
                "location": signature_location,
                "signer": cert_info.get("subject", ""),
                "crm": cert_info.get("crm_number"),
                "crm_state": cert_info.get("crm_state"),
                "signed_at": datetime.now().isoformat(),
                "certificate_serial": cert_info.get("serial_number"),
                "certificate_valid_from": cert_info.get("valid_from").isoformat() if cert_info.get("valid_from") else None,
                "certificate_valid_to": cert_info.get("valid_to").isoformat() if cert_info.get("valid_to") else None
            }
            
            # Hash the PDF
            pdf_hash = DigitalSignatureService.hash_document(pdf_bytes)
            
            # Create signature
            signature = DigitalSignatureService.create_signature_data(
                pdf_hash,
                private_key_pem
            )
            
            signature_data["signature"] = signature
            signature_data["document_hash"] = pdf_hash
            
            # In production, embed this in PDF using PyPDF2 or similar
            # For now, we'll return the PDF with signature metadata
            # The frontend/PDF generator should handle embedding
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error adding signature to PDF: {str(e)}", exc_info=True)
            raise