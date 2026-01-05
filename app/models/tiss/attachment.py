"""
TISS Attachment Model
Stores file attachments for TISS guides
"""

from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.sql import func
from database import Base


class TISSAttachment(Base):
    """TISS Attachment - Anexos de Guias"""
    __tablename__ = "tiss_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Reference to guide (polymorphic)
    guide_id = Column(Integer, nullable=False, index=True)
    guide_type = Column(String(50), nullable=False, index=True)
    # Types: 'consultation', 'sadt', 'hospitalization', 'individual_fee'
    
    # File information
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=True)  # MIME type
    file_size = Column(Integer, nullable=True)  # Size in bytes
    hash_file = Column(String(64), nullable=True)  # SHA-256 hash for integrity
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('ix_tiss_attachments_guide', 'guide_id', 'guide_type'),
    )
    
    def __repr__(self):
        return f"<TISSAttachment(id={self.id}, guide_type='{self.guide_type}', file_name='{self.file_name}')>"

