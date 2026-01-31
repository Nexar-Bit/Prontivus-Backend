"""
TISS Insurance Structure Models
Estrutura completa para gerenciar Convênios, Planos, TUSS vs Planos e valores contratuais
"""

from sqlalchemy import (
    Column, Integer, ForeignKey, String, Date, Boolean, DateTime, 
    Numeric, Text, Index, JSON
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class InsuranceCompany(Base):
    """
    Convênio/Operadora
    Tabela de convênios/operadoras de saúde
    """
    __tablename__ = "tiss_insurance_companies"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Dados da Operadora
    nome = Column(String(200), nullable=False, index=True)
    razao_social = Column(String(200), nullable=True)
    cnpj = Column(String(18), nullable=False, unique=True, index=True)
    registro_ans = Column(String(6), nullable=False, index=True)  # Registro ANS da operadora
    codigo_operadora = Column(String(20), nullable=True, index=True)  # Código interno da operadora
    
    # Contato
    telefone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    endereco = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, server_default='true', index=True)
    
    # Metadados
    observacoes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    # Relationships
    clinic = relationship("Clinic", backref="tiss_insurance_companies")
    plans = relationship("InsurancePlanTISS", back_populates="insurance_company", cascade="all, delete-orphan")
    load_history = relationship("TUSSLoadHistory", back_populates="insurance_company", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_tiss_insurance_companies_clinic_cnpj', 'clinic_id', 'cnpj'),
    )
    
    def __repr__(self):
        return f"<InsuranceCompany(id={self.id}, nome='{self.nome}', registro_ans='{self.registro_ans}')>"


class InsurancePlanTISS(Base):
    """
    Plano do Convênio
    Planos de saúde oferecidos por cada convênio
    """
    __tablename__ = "tiss_insurance_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    insurance_company_id = Column(Integer, ForeignKey("tiss_insurance_companies.id", ondelete="CASCADE"), nullable=False, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Dados do Plano
    nome_plano = Column(String(200), nullable=False, index=True)
    codigo_plano = Column(String(50), nullable=True, index=True)  # Código interno do plano
    numero_plano_ans = Column(String(20), nullable=True)  # Número do plano na ANS
    
    # Cobertura geral
    cobertura_percentual = Column(Numeric(5, 2), nullable=False, server_default='100.00')  # % de cobertura padrão
    requer_autorizacao = Column(Boolean, nullable=False, server_default='false')
    limite_anual = Column(Numeric(12, 2), nullable=True)
    limite_por_procedimento = Column(Numeric(12, 2), nullable=True)
    
    # Vigência
    data_inicio_vigencia = Column(Date, nullable=True)
    data_fim_vigencia = Column(Date, nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, server_default='true', index=True)
    
    # Metadados
    observacoes = Column(Text, nullable=True)
    configuracoes_extras = Column(JSON, nullable=True)  # Configurações adicionais em JSON
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    # Relationships
    insurance_company = relationship("InsuranceCompany", back_populates="plans")
    clinic = relationship("Clinic", backref="tiss_insurance_plans")
    tuss_coverages = relationship("TUSSPlanCoverage", back_populates="insurance_plan", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_tiss_insurance_plans_company_plan', 'insurance_company_id', 'codigo_plano'),
    )
    
    def __repr__(self):
        return f"<InsurancePlanTISS(id={self.id}, nome_plano='{self.nome_plano}', insurance_company_id={self.insurance_company_id})>"


class TUSSPlanCoverage(Base):
    """
    TUSS vs Planos com Valores
    Relaciona códigos TUSS com planos, definindo cobertura e valores contratuais
    """
    __tablename__ = "tiss_tuss_plan_coverage"
    
    id = Column(Integer, primary_key=True, index=True)
    tuss_code_id = Column(Integer, ForeignKey("tiss_tuss_codes.id", ondelete="CASCADE"), nullable=False, index=True)
    insurance_plan_id = Column(Integer, ForeignKey("tiss_insurance_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Cobertura
    coberto = Column(Boolean, nullable=False, server_default='true', index=True)  # Se o procedimento é coberto
    cobertura_percentual = Column(Numeric(5, 2), nullable=False, server_default='100.00')  # % de cobertura específica
    
    # Valores Contratuais
    valor_tabela = Column(Numeric(12, 2), nullable=True)  # Valor da tabela TUSS oficial
    valor_contratual = Column(Numeric(12, 2), nullable=True)  # Valor contratual negociado
    valor_coparticipacao = Column(Numeric(12, 2), nullable=True, server_default='0.00')  # Valor de coparticipação
    valor_franquia = Column(Numeric(12, 2), nullable=True, server_default='0.00')  # Valor de franquia
    
    # Regras de Autorização
    requer_autorizacao = Column(Boolean, nullable=False, server_default='false')
    prazo_autorizacao_dias = Column(Integer, nullable=True)  # Prazo em dias para obter autorização
    limite_quantidade = Column(Integer, nullable=True)  # Limite de quantidade por período
    limite_periodo_dias = Column(Integer, nullable=True)  # Período em dias para o limite
    
    # Vigência
    data_inicio_vigencia = Column(Date, nullable=False, index=True)
    data_fim_vigencia = Column(Date, nullable=True, index=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, server_default='true', index=True)
    
    # Metadados
    observacoes = Column(Text, nullable=True)
    regras_especiais = Column(JSON, nullable=True)  # Regras especiais em JSON
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    # Relationships
    tuss_code = relationship("TUSSCode", backref="plan_coverages")
    insurance_plan = relationship("InsurancePlanTISS", back_populates="tuss_coverages")
    clinic = relationship("Clinic", backref="tiss_tuss_plan_coverages")
    load_history = relationship("TUSSLoadHistory", back_populates="tuss_plan_coverage", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_tiss_tuss_plan_coverage_tuss_plan', 'tuss_code_id', 'insurance_plan_id'),
        Index('ix_tiss_tuss_plan_coverage_vigencia', 'data_inicio_vigencia', 'data_fim_vigencia'),
    )
    
    def __repr__(self):
        return f"<TUSSPlanCoverage(id={self.id}, tuss_code_id={self.tuss_code_id}, insurance_plan_id={self.insurance_plan_id}, coberto={self.coberto})>"


class TUSSLoadHistory(Base):
    """
    Histórico de Cargas TUSS
    Registra cada carga de dados TUSS (upload em massa) mantendo histórico completo
    """
    __tablename__ = "tiss_tuss_load_history"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    insurance_company_id = Column(Integer, ForeignKey("tiss_insurance_companies.id", ondelete="SET NULL"), nullable=True, index=True)
    tuss_plan_coverage_id = Column(Integer, ForeignKey("tiss_tuss_plan_coverage.id", ondelete="SET NULL"), nullable=True)
    
    # Tipo de carga
    tipo_carga = Column(String(50), nullable=False, index=True)
    # Valores: 'tuss_codes', 'insurance_companies', 'insurance_plans', 'tuss_plan_coverage'
    
    # Informações da carga
    nome_arquivo = Column(String(255), nullable=False)
    total_registros = Column(Integer, nullable=False, server_default='0')
    registros_inseridos = Column(Integer, nullable=False, server_default='0')
    registros_atualizados = Column(Integer, nullable=False, server_default='0')
    registros_erro = Column(Integer, nullable=False, server_default='0')
    
    # Detalhes
    versao_tuss = Column(String(20), nullable=True)  # Versão TUSS da carga
    data_referencia = Column(Date, nullable=True)  # Data de referência dos dados
    observacoes = Column(Text, nullable=True)
    
    # Erros e avisos (JSON)
    erros = Column(JSON, nullable=True)  # Lista de erros encontrados
    avisos = Column(JSON, nullable=True)  # Lista de avisos
    
    # Usuário que fez a carga
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    clinic = relationship("Clinic", backref="tiss_load_history")
    insurance_company = relationship("InsuranceCompany", back_populates="load_history")
    tuss_plan_coverage = relationship("TUSSPlanCoverage", back_populates="load_history")
    user = relationship("User", backref="tiss_load_history")
    
    __table_args__ = (
        Index('ix_tiss_load_history_clinic_tipo', 'clinic_id', 'tipo_carga'),
        Index('ix_tiss_load_history_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<TUSSLoadHistory(id={self.id}, tipo_carga='{self.tipo_carga}', total_registros={self.total_registros})>"
