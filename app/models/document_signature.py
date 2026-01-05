"""
Document Signature Model
Stores digital signatures for medical documents (prescriptions, certificates, consultation reports)
using AR CFM (Assinatura Digital com Certificado Digital da Ordem dos Médicos)
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import datetime

from database import Base


class SignatureStatus(str, enum.Enum):
    """Signature status"""
    PENDING = "pending"
    SIGNED = "signed"
    REVOKED = "revoked"
    EXPIRED = "expired"


class DocumentType(str, enum.Enum):
    """Document types that can be signed"""
    PRESCRIPTION = "prescription"
    CERTIFICATE = "certificate"
    CONSULTATION_REPORT = "consultation_report"
    EXAM_REQUEST = "exam_request"
    OTHER = "other"


class DocumentSignature(Base):
    """
    Digital signature for medical documents
    
    Stores:
    - Document reference (type + ID)
    - Doctor who signed
    - Signature data (hash, certificate info, timestamp)
    - AR CFM certificate information
    - Signature status
    """
    __tablename__ = "document_signatures"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Document reference
    document_type = Column(SQLEnum(DocumentType, native_enum=False), nullable=False, index=True)
    document_id = Column(Integer, nullable=False, index=True)  # ID of prescription, appointment, etc.
    
    # Signer information
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    
    # AR CFM Certificate information
    crm_number = Column(String(20), nullable=False)  # CRM number
    crm_state = Column(String(2), nullable=False)  # CRM state (e.g., "SP", "RJ")
    certificate_serial = Column(String(255), nullable=True)  # Certificate serial number
    certificate_issuer = Column(String(255), nullable=True)  # Certificate issuer (AR CFM)
    certificate_valid_from = Column(DateTime(timezone=True), nullable=True)
    certificate_valid_to = Column(DateTime(timezone=True), nullable=True)
    
    # Signature data
    document_hash = Column(String(512), nullable=False)  # SHA-256 hash of the document
    signature_data = Column(Text, nullable=False)  # Base64 encoded signature
    signature_algorithm = Column(String(50), default="RSA-SHA256", nullable=False)
    
    # Metadata
    status = Column(SQLEnum(SignatureStatus, native_enum=False), default=SignatureStatus.SIGNED, nullable=False, index=True)
    signed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(Text, nullable=True)
    
    # IP address and user agent for audit
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    doctor = relationship("User", foreign_keys=[doctor_id])
    clinic = relationship("Clinic")
    
    def __repr__(self):
        return f"<DocumentSignature(id={self.id}, document_type={self.document_type.value}, document_id={self.document_id}, status={self.status.value})>"
