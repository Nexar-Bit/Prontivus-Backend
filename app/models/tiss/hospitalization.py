"""
TISS Hospitalization Guide Model
Stores hospitalization guide data for TISS billing
"""

from sqlalchemy import Column, Integer, ForeignKey, String, Date, Numeric, Text, Boolean, DateTime, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class TISHospitalizationGuide(Base):
    """TISS Hospitalization Guide - Guia de Internação"""
    __tablename__ = "tiss_hospitalization_guides"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    
    # Guide identification
    numero_guia = Column(String(20), nullable=False, index=True)
    data_emissao = Column(Date, nullable=False)
    
    # Guide data
    prestador_data = Column(JSON, nullable=False)
    operadora_data = Column(JSON, nullable=False)
    beneficiario_data = Column(JSON, nullable=False)
    contratado_data = Column(JSON, nullable=False)
    internacao_data = Column(JSON, nullable=False)  # Hospitalization specific data
    
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
    
    # Locking
    is_locked = Column(Boolean, nullable=False, server_default='false')
    
    # Relationships
    clinic = relationship("Clinic", backref="tiss_hospitalization_guides")
    invoice = relationship("Invoice", backref="tiss_hospitalization_guides")
    appointment = relationship("Appointment", backref="tiss_hospitalization_guides")
    
    __table_args__ = (
        Index('ix_tiss_hospitalization_guides_clinic_status', 'clinic_id', 'status'),
    )
    
    def __repr__(self):
        return f"<TISHospitalizationGuide(id={self.id}, numero_guia='{self.numero_guia}', status='{self.status}')>"

