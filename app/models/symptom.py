"""
Symptom Database Models
Stores symptoms and their mappings to ICD-10 codes
"""

import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from database import Base


class Symptom(Base):
    """
    Symptom Model
    Stores common symptoms that can be used for diagnosis
    """
    __tablename__ = "symptoms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    name_normalized = Column(String(100), nullable=False, index=True)  # Lowercase, normalized for search
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # e.g., "respiratory", "cardiovascular", "gastrointestinal"
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.datetime.now)
    
    # Relationships
    icd10_mappings = relationship("SymptomICD10Mapping", back_populates="symptom", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_symptoms_name_normalized', 'name_normalized'),
        Index('ix_symptoms_category', 'category'),
    )
    
    def __repr__(self):
        return f"<Symptom(id={self.id}, name='{self.name}')>"


class SymptomICD10Mapping(Base):
    """
    Symptom to ICD-10 Code Mapping
    Maps symptoms to possible ICD-10 diagnostic codes with confidence/relevance scores
    """
    __tablename__ = "symptom_icd10_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    symptom_id = Column(Integer, ForeignKey("symptoms.id"), nullable=False, index=True)
    icd10_code = Column(String(10), nullable=False, index=True)  # e.g., "J06", "A09.0"
    relevance_score = Column(Integer, default=100, nullable=False)  # 0-100, higher = more relevant
    notes = Column(Text, nullable=True)  # Additional notes about the mapping
    
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now, nullable=False)
    
    # Relationships
    symptom = relationship("Symptom", back_populates="icd10_mappings")
    
    __table_args__ = (
        Index('ix_symptom_icd10_symptom', 'symptom_id'),
        Index('ix_symptom_icd10_code', 'icd10_code'),
        Index('ix_symptom_icd10_relevance', 'relevance_score'),
    )
    
    def __repr__(self):
        return f"<SymptomICD10Mapping(symptom_id={self.symptom_id}, icd10_code='{self.icd10_code}')>"

