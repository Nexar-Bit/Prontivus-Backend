"""
AI Diagnosis API Endpoints
Provides clinical decision support including:
- Symptom analysis and differential diagnosis
- ICD-10 code suggestions
- Drug interaction checking
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Optional
from pydantic import BaseModel
import logging

from app.services.clinical_ai import clinical_ai
from app.core.auth import get_current_user
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Diagnosis"])


# Request/Response Models
class SymptomAnalysisRequest(BaseModel):
    symptoms: List[str]
    patient_data: Optional[Dict] = None


class ICD10SuggestionRequest(BaseModel):
    clinical_findings: str


class DrugInteractionRequest(BaseModel):
    medications: List[str]


@router.post("/symptoms/analyze")
async def analyze_symptoms(
    request: SymptomAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze symptoms and suggest differential diagnoses
    
    Args:
        request: SymptomAnalysisRequest with symptoms list and optional patient data
        current_user: Current authenticated user
    
    Returns:
        Analysis result with differential diagnoses
    """
    try:
        if not request.symptoms or len(request.symptoms) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one symptom is required"
            )
        
        result = await clinical_ai.analyze_symptoms(
            request.symptoms,
            request.patient_data
        )
        
        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get('error', 'Symptom analysis failed')
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Symptom analysis endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Symptom analysis failed: {str(e)}"
        )


@router.post("/icd10/suggest")
async def suggest_icd10_codes(
    request: ICD10SuggestionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Suggest ICD-10 codes based on clinical findings
    
    Args:
        request: ICD10SuggestionRequest with clinical findings text
        current_user: Current authenticated user
    
    Returns:
        List of suggested ICD-10 codes with match scores
    """
    try:
        if not request.clinical_findings or not request.clinical_findings.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Clinical findings text is required"
            )
        
        codes = await clinical_ai.suggest_icd10_codes(request.clinical_findings)
        
        return {
            "success": True,
            "suggested_codes": codes,
            "count": len(codes)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ICD-10 suggestion endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ICD-10 suggestion failed: {str(e)}"
        )


@router.post("/drug-interactions/check")
async def check_drug_interactions(
    request: DrugInteractionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Check for potential drug interactions
    
    Args:
        request: DrugInteractionRequest with list of medications
        current_user: Current authenticated user
    
    Returns:
        List of potential drug interactions
    """
    try:
        if not request.medications or len(request.medications) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one medication is required"
            )
        
        interactions = await clinical_ai.check_drug_interactions(request.medications)
        
        return {
            "success": True,
            "interactions": interactions,
            "count": len(interactions),
            "medications_checked": request.medications
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Drug interaction check endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Drug interaction check failed: {str(e)}"
        )


@router.get("/symptoms/database")
async def get_symptoms_database(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available symptoms in the database
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        List of available symptoms
    """
    try:
        symptoms = list(clinical_ai.symptom_database.keys())
        
        return {
            "success": True,
            "symptoms": symptoms,
            "count": len(symptoms)
        }
        
    except Exception as e:
        logger.error(f"Get symptoms database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get symptoms database: {str(e)}"
        )

