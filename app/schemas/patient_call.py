from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PatientCallResponse(BaseModel):
    id: int
    appointment_id: int
    patient_id: int
    doctor_id: int
    clinic_id: int
    status: str
    called_at: datetime
    answered_at: Optional[datetime] = None
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    secretary_name: Optional[str] = None
    call_type: Optional[str] = None  # "doctor_to_patient" or "patient_to_secretary"
    room_number: Optional[str] = None

    class Config:
        from_attributes = True


class PatientCallCreate(BaseModel):
    appointment_id: int


class PatientCallSecretaryCreate(BaseModel):
    """Schema for patient calling secretary - no appointment required"""
    reason: Optional[str] = None  # Optional reason for the call


class PatientCallUpdate(BaseModel):
    status: Optional[str] = None
    answered_at: Optional[datetime] = None

