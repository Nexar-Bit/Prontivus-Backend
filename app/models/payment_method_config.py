"""
Payment Method Configuration Model
Stores per-clinic payment method configurations (active status, default method, etc.)
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class PaymentMethodConfig(Base):
    """
    Payment Method Configuration Model
    Stores configuration for each payment method per clinic
    """
    __tablename__ = "payment_method_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    method = Column(String(50), nullable=False)  # PaymentMethod enum value
    name = Column(String(100), nullable=False)  # Display name (e.g., "Dinheiro", "PIX")
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)  # Order in UI
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    clinic = relationship("Clinic")
    
    __table_args__ = (
        UniqueConstraint('clinic_id', 'method', name='uq_payment_method_config_clinic_method'),
    )
    
    def __repr__(self):
        return f"<PaymentMethodConfig(clinic_id={self.clinic_id}, method='{self.method}', is_active={self.is_active})>"

