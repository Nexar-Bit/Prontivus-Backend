"""
Report Configuration Model
Stores per-clinic report configuration settings
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime, JSON, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class ReportConfig(Base):
    """
    Report Configuration Model
    Stores configuration for reports per clinic
    """
    __tablename__ = "report_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True, unique=True)
    
    # Financial Reports Configuration
    financial = Column(JSON, nullable=False, default=dict)
    # Example structure:
    # {
    #   "enabled": true,
    #   "detailed": true
    # }
    
    # Clinical Reports Configuration
    clinical = Column(JSON, nullable=False, default=dict)
    # Example structure:
    # {
    #   "enabled": true,
    #   "anonymize": false
    # }
    
    # Operational Reports Configuration
    operational = Column(JSON, nullable=False, default=dict)
    # Example structure:
    # {
    #   "enabled": true,
    #   "automatic_scheduling": false
    # }
    
    # General Settings
    general = Column(JSON, nullable=False, default=dict)
    # Example structure:
    # {
    #   "allow_export": true,
    #   "send_by_email": false
    # }
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    clinic = relationship("Clinic")
    
    __table_args__ = (
        UniqueConstraint('clinic_id', name='uq_report_config_clinic'),
    )
    
    def __repr__(self):
        return f"<ReportConfig(clinic_id={self.clinic_id})>"

