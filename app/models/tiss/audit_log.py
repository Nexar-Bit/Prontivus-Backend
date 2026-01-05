"""
TISS Audit Log Model
Immutable audit trail for TISS operations (LGPD compliance)
"""

from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class TISSAuditLog(Base):
    """TISS Audit Log - Log de Auditoria Imutável"""
    __tablename__ = "tiss_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Action information
    action = Column(String(50), nullable=False)
    # Actions: 'create', 'update', 'delete', 'submit', 'view', 'download', 'export'
    
    # Entity information
    entity_type = Column(String(50), nullable=False)
    # Types: 'consultation_guide', 'sadt_guide', 'hospitalization_guide', 'batch', etc.
    entity_id = Column(Integer, nullable=True)
    
    # Change tracking
    changes = Column(JSON, nullable=True)  # Before/after changes
    
    # Request information
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    
    # Timestamp (immutable - never updated)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    clinic = relationship("Clinic", backref="tiss_audit_logs")
    user = relationship("User", backref="tiss_audit_logs")
    
    __table_args__ = (
        Index('ix_tiss_audit_logs_entity', 'entity_type', 'entity_id'),
        Index('ix_tiss_audit_logs_clinic_created', 'clinic_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<TISSAuditLog(id={self.id}, action='{self.action}', entity_type='{self.entity_type}')>"

