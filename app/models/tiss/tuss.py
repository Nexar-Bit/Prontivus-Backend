"""
TUSS (Terminologia Unificada da Saúde Suplementar) Models
Stores TUSS codes and version history
"""

from sqlalchemy import Column, Integer, ForeignKey, String, Date, Boolean, DateTime, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class TUSSCode(Base):
    """TUSS Code - Código TUSS"""
    __tablename__ = "tiss_tuss_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # TUSS code information
    codigo = Column(String(10), nullable=False, index=True)
    descricao = Column(String(500), nullable=False)
    tabela = Column(String(2), nullable=False, index=True)
    # Tables: '01'=Consultas, '02'=Procedimentos, '03'=Exames, etc.
    
    # Validity period
    data_inicio_vigencia = Column(Date, nullable=False)
    data_fim_vigencia = Column(Date, nullable=True)
    
    # Versioning
    versao_tuss = Column(String(20), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default='true')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    # Relationships
    version_history = relationship("TUSSVersionHistory", back_populates="tuss_code", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_tiss_tuss_codes_codigo_tabela', 'codigo', 'tabela'),
    )
    
    def __repr__(self):
        return f"<TUSSCode(id={self.id}, codigo='{self.codigo}', tabela='{self.tabela}')>"


class TUSSVersionHistory(Base):
    """TUSS Version History - Histórico de Versões TUSS"""
    __tablename__ = "tiss_tuss_version_history"
    
    id = Column(Integer, primary_key=True, index=True)
    tuss_code_id = Column(Integer, ForeignKey("tiss_tuss_codes.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Version information
    versao_anterior = Column(String(20), nullable=True)
    versao_nova = Column(String(20), nullable=False)
    data_alteracao = Column(Date, nullable=False)
    motivo = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    tuss_code = relationship("TUSSCode", back_populates="version_history")
    
    def __repr__(self):
        return f"<TUSSVersionHistory(id={self.id}, tuss_code_id={self.tuss_code_id}, versao_nova='{self.versao_nova}')>"

