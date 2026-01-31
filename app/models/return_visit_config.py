"""
Return Visit Configuration Model
Manages return visit policies and limits per doctor
"""

from sqlalchemy import Column, Integer, ForeignKey, Boolean, String, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class ReturnVisitConfig(Base):
    """
    Return Visit Configuration
    Defines return visit policies for each doctor
    """
    __tablename__ = "return_visit_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Return visit rules
    enable_return_limit = Column(Boolean, default=True, nullable=False)
    return_window_days = Column(Integer, default=30, nullable=False)  # Days to consider as return visit
    daily_return_limit = Column(Integer, default=5, nullable=False)  # Max returns per day
    monthly_return_limit = Column(Integer, default=50, nullable=True)  # Max returns per month (optional)
    
    # Approval settings
    require_approval_when_exceeded = Column(Boolean, default=True, nullable=False)
    approval_message = Column(String(500), nullable=True)
    
    # Additional rules (JSON for flexibility)
    custom_rules = Column(JSON, nullable=True)
    # Example: {"block_same_day_return": true, "min_hours_between_returns": 24}
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    clinic = relationship("Clinic", backref="return_visit_configs")
    doctor = relationship("User", backref="return_visit_configs")
    
    def __repr__(self):
        return f"<ReturnVisitConfig(doctor_id={self.doctor_id}, daily_limit={self.daily_return_limit})>"


class ReturnVisitApproval(Base):
    """
    Return Visit Approval Requests
    Tracks approval requests when return limits are exceeded
    """
    __tablename__ = "return_visit_approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Approval details
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Secretary who requested
    reason = Column(String(500), nullable=False)
    
    # Status
    status = Column(String(20), default="pending", nullable=False, index=True)
    # Values: pending, approved, rejected
    
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approval_notes = Column(String(500), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    clinic = relationship("Clinic", backref="return_visit_approvals")
    appointment = relationship("Appointment", backref="return_approvals")
    patient = relationship("Patient", foreign_keys=[patient_id], backref="return_visit_approvals")
    doctor = relationship("User", foreign_keys=[doctor_id], backref="doctor_return_approvals")
    requester = relationship("User", foreign_keys=[requested_by], backref="requested_return_approvals")
    approver = relationship("User", foreign_keys=[approved_by], backref="approved_return_approvals")
    
    def __repr__(self):
        return f"<ReturnVisitApproval(appointment_id={self.appointment_id}, status={self.status})>"
