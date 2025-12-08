"""
Appointment Pydantic schemas for request/response validation
"""
import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from app.models import AppointmentStatus
from app.models.financial import PaymentMethod


class AppointmentBase(BaseModel):
    scheduled_datetime: datetime.datetime
    appointment_type: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    reason: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    patient_id: int
    doctor_id: int
    clinic_id: int
    consultation_price: Optional[Decimal] = Field(None, description="Consultation price (if different from doctor's default)")
    payment_method: Optional[PaymentMethod] = Field(None, description="Preferred payment method for this appointment")
    create_invoice: Optional[bool] = Field(False, description="Whether to auto-create invoice for this appointment")


class AppointmentUpdate(BaseModel):
    scheduled_datetime: Optional[datetime.datetime] = None
    appointment_type: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    reason: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class AppointmentResponse(BaseModel):
    id: int
    scheduled_datetime: datetime.datetime
    status: AppointmentStatus
    appointment_type: Optional[str]
    notes: Optional[str]
    reason: Optional[str]
    diagnosis: Optional[str]
    treatment_plan: Optional[str]
    patient_id: int
    doctor_id: int
    clinic_id: int
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]
    
    # Include related data
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class AppointmentListResponse(BaseModel):
    id: int
    scheduled_datetime: datetime.datetime
    status: AppointmentStatus
    appointment_type: Optional[str]
    patient_id: int
    doctor_id: int
    patient_name: str
    doctor_name: str
    
    class Config:
        from_attributes = True

