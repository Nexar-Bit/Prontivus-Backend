"""
Pydantic schemas for document signature
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.document_signature import SignatureStatus, DocumentType


class DocumentSignatureBase(BaseModel):
    document_type: DocumentType
    document_id: int
    crm_number: str = Field(..., description="CRM number")
    crm_state: str = Field(..., description="CRM state (e.g., 'SP', 'RJ')", max_length=2)


class DocumentSignatureCreate(DocumentSignatureBase):
    """Request to create a signature"""
    document_hash: str = Field(..., description="SHA-256 hash of the document")
    signature_data: str = Field(..., description="Base64 encoded signature")
    signature_algorithm: str = Field(default="RSA-SHA256", description="Signature algorithm")
    certificate_serial: Optional[str] = None
    certificate_issuer: Optional[str] = None
    certificate_valid_from: Optional[datetime] = None
    certificate_valid_to: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class DocumentSignatureResponse(BaseModel):
    """Response with signature information"""
    id: int
    document_type: DocumentType
    document_id: int
    doctor_id: int
    clinic_id: int
    crm_number: str
    crm_state: str
    certificate_serial: Optional[str] = None
    certificate_issuer: Optional[str] = None
    certificate_valid_from: Optional[datetime] = None
    certificate_valid_to: Optional[datetime] = None
    document_hash: str
    signature_algorithm: str
    status: SignatureStatus
    signed_at: datetime
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Doctor information
    doctor_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class DocumentSignatureVerifyRequest(BaseModel):
    """Request to verify a signature"""
    document_type: DocumentType
    document_id: int
    document_hash: Optional[str] = None  # If provided, verify hash matches


class DocumentSignatureVerifyResponse(BaseModel):
    """Response from signature verification"""
    is_valid: bool
    signature: Optional[DocumentSignatureResponse] = None
    error: Optional[str] = None
    message: Optional[str] = None


class DocumentSignatureRevokeRequest(BaseModel):
    """Request to revoke a signature"""
    revocation_reason: str = Field(..., description="Reason for revocation")
