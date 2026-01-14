"""
Return Approval Request Model
Handles approval requests for multiple return appointments per month
"""
import enum
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text, String, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class ReturnApprovalStatus(str, enum.Enum):
    """Return approval request status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ReturnApprovalRequest(Base):
    """
    Return Approval Request Model
    Used when a secretary requests approval for multiple return appointments in the same month
    """
    __tablename__ = "return_approval_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Appointment details
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    
    # Request details
    requested_appointment_date = Column(DateTime(timezone=True), nullable=False)
    appointment_type = Column(String(100), nullable=False, default="retorno")
    notes = Column(Text, nullable=True)  # Reason for the request
    returns_count_this_month = Column(Integer, nullable=False, default=0)  # Current count of returns
    
    # Approval workflow
    status = Column(SQLEnum(ReturnApprovalStatus), nullable=False, default=ReturnApprovalStatus.PENDING, index=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Secretary who requested
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Doctor who approved/rejected
    approval_notes = Column(Text, nullable=True)  # Doctor's notes on approval/rejection
    
    # Resulting appointment (created after approval)
    resulting_appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True, index=True)
    
    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Auto-expire after 7 days
    
    # Relationships
    patient = relationship("Patient", back_populates="return_approval_requests")
    doctor = relationship("User", foreign_keys=[doctor_id], back_populates="return_approval_requests_as_doctor")
    clinic = relationship("Clinic", back_populates="return_approval_requests")
    requester = relationship("User", foreign_keys=[requested_by], back_populates="return_approval_requests_created")
    approver = relationship("User", foreign_keys=[approved_by], back_populates="return_approval_requests_approved")
    resulting_appointment = relationship("Appointment", foreign_keys=[resulting_appointment_id], back_populates="return_approval_request")
    
    def __repr__(self):
        return f"<ReturnApprovalRequest(id={self.id}, patient_id={self.patient_id}, status={self.status})>"
