"""
Telemetry Model
Stores patient health metrics and vital signs data for monitoring and tracking
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class PatientTelemetry(Base):
    """
    Patient Telemetry / Vital Signs Tracking
    
    Stores:
    - Vital signs (blood pressure, heart rate, temperature, oxygen saturation, etc.)
    - Weight, height, BMI
    - Activity metrics (steps, calories, etc.)
    - Sleep data
    - Custom metrics
    """
    __tablename__ = "patient_telemetry"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Patient reference
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    
    # Measurement timestamp
    measured_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Vital Signs
    systolic_bp = Column(Numeric(5, 2), nullable=True)  # Systolic blood pressure (mmHg)
    diastolic_bp = Column(Numeric(5, 2), nullable=True)  # Diastolic blood pressure (mmHg)
    heart_rate = Column(Numeric(5, 2), nullable=True)  # Heart rate (bpm)
    temperature = Column(Numeric(5, 2), nullable=True)  # Temperature (°C or °F)
    oxygen_saturation = Column(Numeric(5, 2), nullable=True)  # SpO2 (%)
    respiratory_rate = Column(Numeric(5, 2), nullable=True)  # Respiratory rate (breaths/min)
    
    # Body metrics
    weight = Column(Numeric(6, 2), nullable=True)  # Weight (kg)
    height = Column(Numeric(5, 2), nullable=True)  # Height (cm)
    bmi = Column(Numeric(5, 2), nullable=True)  # Body Mass Index
    
    # Activity metrics
    steps = Column(Integer, nullable=True)  # Steps count
    calories_burned = Column(Numeric(8, 2), nullable=True)  # Calories burned
    activity_minutes = Column(Integer, nullable=True)  # Active minutes
    
    # Sleep metrics
    sleep_hours = Column(Numeric(4, 2), nullable=True)  # Sleep duration (hours)
    sleep_quality = Column(String(20), nullable=True)  # sleep quality rating
    
    # Blood glucose (for diabetes monitoring)
    blood_glucose = Column(Numeric(5, 2), nullable=True)  # Blood glucose (mg/dL)
    
    # Additional metrics stored as JSON
    additional_metrics = Column(JSON, nullable=True)  # Custom metrics
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Source/Device
    source = Column(String(50), nullable=True)  # manual, wearable, device_name
    device_id = Column(String(100), nullable=True)  # Device identifier if applicable
    
    # Metadata
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who recorded (if manual)
    is_verified = Column(Boolean, default=False, nullable=False)  # Verified by healthcare provider
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="telemetry_records")
    clinic = relationship("Clinic")
    recorder = relationship("User", foreign_keys=[recorded_by])
    
    def __repr__(self):
        return f"<PatientTelemetry(id={self.id}, patient_id={self.patient_id}, measured_at={self.measured_at})>"
