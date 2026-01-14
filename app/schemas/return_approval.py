"""
Return Approval Request Schemas
"""
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, Field


class ReturnApprovalRequestCreate(BaseModel):
    """Schema for creating a return approval request"""
    patient_id: int
    doctor_id: int
    requested_appointment_date: datetime
    appointment_type: str = "retorno"
    notes: Optional[str] = None
    returns_count_this_month: int = Field(..., ge=0)


class ReturnApprovalRequestUpdate(BaseModel):
    """Schema for updating a return approval request"""
    status: Optional[str] = None  # "approved" or "rejected"
    approval_notes: Optional[str] = None


class ReturnApprovalRequestResponse(BaseModel):
    """Schema for return approval request response"""
    id: int
    patient_id: int
    doctor_id: int
    clinic_id: int
    requested_appointment_date: datetime
    appointment_type: str
    notes: Optional[str] = None
    returns_count_this_month: int
    status: str
    requested_by: int
    approved_by: Optional[int] = None
    approval_notes: Optional[str] = None
    resulting_appointment_id: Optional[int] = None
    requested_at: datetime
    reviewed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Related data
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    requester_name: Optional[str] = None
    approver_name: Optional[str] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
