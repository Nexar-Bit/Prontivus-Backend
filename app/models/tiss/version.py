"""
TISS Version Model
Stores TISS standard versions and XSD files
"""

from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, Text
from sqlalchemy.sql import func
from database import Base


class TISSVersion(Base):
    """TISS Version - Versão do Padrão TISS"""
    __tablename__ = "tiss_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Version information
    version = Column(String(20), nullable=False, unique=True, index=True)
    # Examples: '3.05.02', '3.03.00'
    
    xsd_file_path = Column(String(500), nullable=True)  # Path to XSD file
    is_active = Column(Boolean, nullable=False, server_default='true')
    
    # Lifecycle
    release_date = Column(Date, nullable=True)
    end_of_life_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<TISSVersion(id={self.id}, version='{self.version}', is_active={self.is_active})>"

