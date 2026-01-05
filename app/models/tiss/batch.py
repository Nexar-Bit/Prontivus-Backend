"""
TISS Batch Model
Stores batch (lote) data for TISS submissions
"""

from sqlalchemy import Column, Integer, ForeignKey, String, Date, Numeric, Text, Boolean, DateTime, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class TISSBatch(Base):
    """TISS Batch - Lote de Guias"""
    __tablename__ = "tiss_batches"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Batch identification
    numero_lote = Column(String(20), nullable=False, index=True)
    data_envio = Column(Date, nullable=False)
    hora_envio = Column(String(5), nullable=True)  # HH:MM format
    
    # Guides in batch
    guias_ids = Column(JSON, nullable=False)  # Array of guide IDs
    guias_tipo = Column(String(20), nullable=False)  # 'consultation', 'sadt', 'hospitalization', 'individual_fee'
    
    # Batch content
    xml_content = Column(Text, nullable=True)
    hash_integridade = Column(String(64), nullable=True)
    
    # Submission tracking
    submission_status = Column(String(20), nullable=False, server_default='pending', index=True)
    submission_method = Column(String(20), nullable=True)  # 'soap', 'rest', 'sftp', 'manual'
    retry_count = Column(Integer, nullable=False, server_default='0')
    max_retries = Column(Integer, nullable=False, server_default='3')
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    protocol_number = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Financial
    valor_total_lote = Column(Numeric(12, 2), nullable=True)
    
    # Versioning
    versao_tiss = Column(String(20), nullable=False, server_default='3.05.02')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    clinic = relationship("Clinic", backref="tiss_batches")
    statements = relationship("TISSStatement", back_populates="batch", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_tiss_batches_clinic_status', 'clinic_id', 'submission_status'),
    )
    
    def __repr__(self):
        return f"<TISSBatch(id={self.id}, numero_lote='{self.numero_lote}', status='{self.submission_status}')>"

