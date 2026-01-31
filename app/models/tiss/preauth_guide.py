"""
TISS Pre-Authorization Guide Model
Modelo para Guias de Solicitação de Autorização TISS
"""

from sqlalchemy import (
    Column, Integer, ForeignKey, String, Date, Boolean, DateTime, 
    Numeric, Text, JSON, Enum as SQLEnum
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum


class PreAuthGuideStatus(str, enum.Enum):
    """Status da Guia de Solicitação de Autorização"""
    DRAFT = "draft"  # Rascunho
    PENDING = "pending"  # Enviada, aguardando resposta
    APPROVED = "approved"  # Aprovada
    DENIED = "denied"  # Negada
    EXPIRED = "expired"  # Expirada
    CANCELLED = "cancelled"  # Cancelada


class PreAuthGuideSubmissionStatus(str, enum.Enum):
    """Status de envio da guia"""
    NOT_SENT = "not_sent"  # Não enviada
    SENT = "sent"  # Enviada
    ERROR = "error"  # Erro no envio
    RETRYING = "retrying"  # Tentando reenviar


class TISSPreAuthGuide(Base):
    """
    Guia de Solicitação de Autorização TISS
    Representa uma guia de solicitação de autorização enviada ao convênio
    """
    __tablename__ = "tiss_preauth_guides"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    insurance_company_id = Column(Integer, ForeignKey("tiss_insurance_companies.id", ondelete="SET NULL"), nullable=True, index=True)
    insurance_plan_id = Column(Integer, ForeignKey("tiss_insurance_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Número da guia
    numero_guia = Column(String(50), unique=True, nullable=False, index=True)  # Número único da guia
    numero_guia_operadora = Column(String(50), nullable=True, index=True)  # Número retornado pela operadora
    
    # Código TUSS do procedimento
    tuss_code_id = Column(Integer, ForeignKey("tiss_tuss_codes.id", ondelete="SET NULL"), nullable=True, index=True)
    tuss_code = Column(String(10), nullable=False)  # Código TUSS (mantido para referência)
    tuss_descricao = Column(String(500), nullable=False)
    tabela_tuss = Column(String(2), nullable=False)
    
    # Valores
    valor_solicitado = Column(Numeric(12, 2), nullable=False)
    valor_aprovado = Column(Numeric(12, 2), nullable=True)
    valor_coparticipacao = Column(Numeric(12, 2), nullable=True)
    
    # Status
    status = Column(SQLEnum(PreAuthGuideStatus), nullable=False, default=PreAuthGuideStatus.DRAFT, index=True)
    submission_status = Column(SQLEnum(PreAuthGuideSubmissionStatus), nullable=False, default=PreAuthGuideSubmissionStatus.NOT_SENT, index=True)
    
    # Datas
    data_solicitacao = Column(Date, nullable=False, index=True)
    data_prevista_procedimento = Column(Date, nullable=False)
    data_resposta = Column(Date, nullable=True)
    data_validade = Column(Date, nullable=True)  # Data de validade da autorização
    data_expiracao = Column(Date, nullable=True)  # Data de expiração da solicitação
    
    # Informações de envio
    metodo_envio = Column(String(20), nullable=True)  # 'xml', 'webservice', 'manual'
    xml_content = Column(Text, nullable=True)  # Conteúdo XML gerado
    xml_file_path = Column(String(500), nullable=True)  # Caminho do arquivo XML
    
    # Resposta da operadora
    resposta_operadora = Column(Text, nullable=True)  # Resposta completa da operadora
    protocolo_operadora = Column(String(100), nullable=True)  # Número de protocolo
    motivo_negacao = Column(Text, nullable=True)  # Motivo da negativa (se negada)
    
    # Tentativas de envio
    tentativas_envio = Column(Integer, nullable=False, server_default='0')
    ultima_tentativa_envio = Column(DateTime(timezone=True), nullable=True)
    proxima_tentativa_envio = Column(DateTime(timezone=True), nullable=True)
    
    # Observações
    observacoes = Column(Text, nullable=True)
    dados_adicionais = Column(JSON, nullable=True)  # Dados adicionais em JSON
    
    # Usuário que criou
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)  # Data de envio
    
    # Relationships
    clinic = relationship("Clinic", backref="tiss_preauth_guides")
    appointment = relationship("Appointment", backref="preauth_guides")
    patient = relationship("Patient", backref="preauth_guides")
    insurance_company = relationship("InsuranceCompany", backref="preauth_guides")
    insurance_plan = relationship("InsurancePlanTISS", backref="preauth_guides")
    tuss_code_obj = relationship("TUSSCode", backref="preauth_guides")
    creator = relationship("User", backref="created_preauth_guides")
    
    def __repr__(self):
        return f"<TISSPreAuthGuide(id={self.id}, numero_guia='{self.numero_guia}', status='{self.status}')>"
    
    @property
    def is_approved(self) -> bool:
        """Verifica se a guia foi aprovada"""
        return self.status == PreAuthGuideStatus.APPROVED
    
    @property
    def is_pending(self) -> bool:
        """Verifica se a guia está pendente"""
        return self.status == PreAuthGuideStatus.PENDING
    
    @property
    def is_expired(self) -> bool:
        """Verifica se a guia expirou"""
        if self.status == PreAuthGuideStatus.EXPIRED:
            return True
        if self.data_expiracao:
            from datetime import date
            return date.today() > self.data_expiracao
        return False
