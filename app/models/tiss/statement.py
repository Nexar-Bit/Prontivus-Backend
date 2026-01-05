"""
TISS Statement Model
Stores received statements (demonstrativos) from operators
"""

from sqlalchemy import Column, Integer, ForeignKey, String, Text, Boolean, DateTime, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class TISSStatement(Base):
    """TISS Statement - Demonstrativo Recebido"""
    __tablename__ = "tiss_statements"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("tiss_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Statement type
    tipo_demonstrativo = Column(String(50), nullable=False, index=True)
    # Types: 'protocolo_recebimento', 'demonstrativo_retorno', 'demonstrativo_pagamento'
    
    # Received data
    numero_protocolo = Column(String(100), nullable=True)
    xml_recebido = Column(Text, nullable=False)
    parsed_data = Column(JSON, nullable=True)  # Parsed XML data
    
    # Processing status
    status_processamento = Column(String(20), nullable=False, server_default='pending')
    # Status: 'pending', 'processing', 'processed', 'error'
    
    errors = Column(JSON, nullable=True)  # Array of error objects
    warnings = Column(JSON, nullable=True)  # Array of warning objects
    
    # Timestamps
    data_recebimento = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    batch = relationship("TISSBatch", back_populates="statements")
    clinic = relationship("Clinic", backref="tiss_statements")
    
    __table_args__ = (
        Index('ix_tiss_statements_clinic_tipo', 'clinic_id', 'tipo_demonstrativo'),
    )
    
    def __repr__(self):
        return f"<TISSStatement(id={self.id}, tipo='{self.tipo_demonstrativo}', status='{self.status_processamento}')>"

