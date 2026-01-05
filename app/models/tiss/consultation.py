"""
TISS Consultation Guide Model
Stores consultation guide data for TISS billing
"""

from sqlalchemy import Column, Integer, ForeignKey, String, Date, Numeric, Text, Boolean, DateTime, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class TISSConsultationGuide(Base):
    """TISS Consultation Guide - Guia de Consulta"""
    __tablename__ = "tiss_consultation_guides"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    
    # Guide identification
    numero_guia = Column(String(20), nullable=False, index=True)
    tipo_guia = Column(String(1), nullable=False, server_default='1')  # 1=Consulta
    data_emissao = Column(Date, nullable=False)
    
    # Guide data (stored as JSON for flexibility)
    prestador_data = Column(JSON, nullable=False)
    operadora_data = Column(JSON, nullable=False)
    beneficiario_data = Column(JSON, nullable=False)
    contratado_data = Column(JSON, nullable=False)
    procedimentos_data = Column(JSON, nullable=True)
    
    # Financial
    valor_total = Column(Numeric(10, 2), nullable=False)
    
    # Status and versioning
    status = Column(String(20), nullable=False, server_default='draft', index=True)
    hash_integridade = Column(String(64), nullable=True)
    xml_content = Column(Text, nullable=True)
    versao_tiss = Column(String(20), nullable=False, server_default='3.05.02')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Locking (prevents editing after submission)
    is_locked = Column(Boolean, nullable=False, server_default='false')
    
    # Relationships
    clinic = relationship("Clinic", backref="tiss_consultation_guides")
    invoice = relationship("Invoice", backref="tiss_consultation_guides")
    appointment = relationship("Appointment", backref="tiss_consultation_guides")
    
    __table_args__ = (
        Index('ix_tiss_consultation_guides_clinic_status', 'clinic_id', 'status'),
    )
    
    def __repr__(self):
        return f"<TISSConsultationGuide(id={self.id}, numero_guia='{self.numero_guia}', status='{self.status}')>"

