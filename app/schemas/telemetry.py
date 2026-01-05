"""
Pydantic schemas for patient telemetry/vital signs
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class TelemetryBase(BaseModel):
    measured_at: datetime = Field(..., description="Measurement timestamp")
    
    # Vital Signs
    systolic_bp: Optional[float] = Field(None, description="Systolic blood pressure (mmHg)")
    diastolic_bp: Optional[float] = Field(None, description="Diastolic blood pressure (mmHg)")
    heart_rate: Optional[float] = Field(None, description="Heart rate (bpm)")
    temperature: Optional[float] = Field(None, description="Temperature (°C)")
    oxygen_saturation: Optional[float] = Field(None, description="Oxygen saturation (%)")
    respiratory_rate: Optional[float] = Field(None, description="Respiratory rate (breaths/min)")
    
    # Body metrics
    weight: Optional[float] = Field(None, description="Weight (kg)")
    height: Optional[float] = Field(None, description="Height (cm)")
    bmi: Optional[float] = Field(None, description="Body Mass Index")
    
    # Activity metrics
    steps: Optional[int] = Field(None, description="Steps count")
    calories_burned: Optional[float] = Field(None, description="Calories burned")
    activity_minutes: Optional[int] = Field(None, description="Active minutes")
    
    # Sleep metrics
    sleep_hours: Optional[float] = Field(None, description="Sleep duration (hours)")
    sleep_quality: Optional[str] = Field(None, description="Sleep quality rating")
    
    # Blood glucose
    blood_glucose: Optional[float] = Field(None, description="Blood glucose (mg/dL)")
    
    # Additional data
    additional_metrics: Optional[dict] = Field(None, description="Custom metrics")
    notes: Optional[str] = None
    source: Optional[str] = Field("manual", description="Source: manual, wearable, device_name")
    device_id: Optional[str] = None


class TelemetryCreate(TelemetryBase):
    """Request to create telemetry record"""
    patient_id: Optional[int] = None  # Optional, can be inferred from current user


class TelemetryResponse(TelemetryBase):
    """Response with telemetry record"""
    id: int
    patient_id: int
    clinic_id: int
    is_verified: bool
    recorded_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TelemetryUpdate(BaseModel):
    """Update telemetry record (partial)"""
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    heart_rate: Optional[float] = None
    temperature: Optional[float] = None
    oxygen_saturation: Optional[float] = None
    respiratory_rate: Optional[float] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    bmi: Optional[float] = None
    steps: Optional[int] = None
    calories_burned: Optional[float] = None
    activity_minutes: Optional[int] = None
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[str] = None
    blood_glucose: Optional[float] = None
    additional_metrics: Optional[dict] = None
    notes: Optional[str] = None
    is_verified: Optional[bool] = None


class TelemetryStatsResponse(BaseModel):
    """Aggregated telemetry statistics"""
    period: str
    patient_id: int
    average_systolic_bp: Optional[float] = None
    average_diastolic_bp: Optional[float] = None
    average_heart_rate: Optional[float] = None
    average_temperature: Optional[float] = None
    average_oxygen_saturation: Optional[float] = None
    average_weight: Optional[float] = None
    average_bmi: Optional[float] = None
    total_steps: Optional[int] = None
    average_calories: Optional[float] = None
    average_sleep_hours: Optional[float] = None
    record_count: int
