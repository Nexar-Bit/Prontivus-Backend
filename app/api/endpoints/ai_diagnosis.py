"""
AI Diagnosis API Endpoints
Provides clinical decision support including:
- Symptom analysis and differential diagnosis
- ICD-10 code suggestions
- Drug interaction checking

Now uses real database for ICD-10 codes and symptoms
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Optional
from pydantic import BaseModel
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.clinical_ai import clinical_ai
from app.core.auth import get_current_user
from app.models import User, Symptom
from database import get_async_session
from sqlalchemy import select

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
    use_ai: bool = Query(False, description="Use AI service for enhanced diagnosis"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Analyze symptoms and suggest differential diagnoses
    Now uses real database for symptom and ICD-10 lookups
    
    Args:
        request: SymptomAnalysisRequest with symptoms list and optional patient data
        use_ai: Whether to use AI service for enhanced diagnosis (requires AI config)
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Analysis result with differential diagnoses
    """
    try:
        if not request.symptoms or len(request.symptoms) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one symptom is required"
            )
        
        # Get AI service if requested
        ai_service = None
        if use_ai:
            try:
                from app.api.endpoints.ai_usage import _get_ai_config_with_validation
                from app.services.ai_service import create_ai_service
                
                ai_config, _ = await _get_ai_config_with_validation(
                    db, 
                    current_user.clinic_id, 
                    check_enabled=True
                )
                
                ai_service = create_ai_service(
                    provider=ai_config.provider,
                    api_key_encrypted=ai_config.api_key_encrypted,
                    model=ai_config.model,
                    base_url=ai_config.base_url,
                    max_tokens=ai_config.max_tokens,
                    temperature=ai_config.temperature
                )
            except Exception as e:
                logger.warning(f"AI service not available, using database only: {str(e)}")
                use_ai = False
        
        result = await clinical_ai.analyze_symptoms(
            db=db,
            symptoms=request.symptoms,
            patient_data=request.patient_data,
            use_ai=use_ai,
            ai_service=ai_service
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
        logger.error(f"Symptom analysis endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Symptom analysis failed: {str(e)}"
        )


@router.post("/icd10/suggest")
async def suggest_icd10_codes(
    request: ICD10SuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Suggest ICD-10 codes based on clinical findings
    Now uses real database search index
    
    Args:
        request: ICD10SuggestionRequest with clinical findings text
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of suggested ICD-10 codes with match scores
    """
    try:
        if not request.clinical_findings or not request.clinical_findings.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Clinical findings text is required"
            )
        
        codes = await clinical_ai.suggest_icd10_codes(
            db=db,
            clinical_findings=request.clinical_findings
        )
        
        return {
            "success": True,
            "suggested_codes": codes,
            "count": len(codes)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ICD-10 suggestion endpoint error: {str(e)}", exc_info=True)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get list of available symptoms in the database
    Now queries real database table
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of available symptoms
    """
    try:
        # Query symptoms from database
        result = await db.execute(
            select(Symptom)
            .where(Symptom.is_active == True)
            .order_by(Symptom.name)
        )
        symptoms_list = result.scalars().all()
        
        if not symptoms_list:
            # Fallback to hardcoded data if database is empty
            logger.warning("Symptom database is empty, using fallback")
            symptom_db = clinical_ai.fallback_symptom_database
            symptoms = list(symptom_db.keys())
        else:
            symptoms = [symptom.name for symptom in symptoms_list]
        
        return {
            "success": True,
            "symptoms": symptoms,
            "count": len(symptoms),
            "source": "database" if symptoms_list else "fallback"
        }
        
    except Exception as e:
        logger.error(f"Get symptoms database error: {str(e)}", exc_info=True)
        # Fallback to hardcoded data on error
        try:
            symptom_db = clinical_ai.fallback_symptom_database
            symptoms = list(symptom_db.keys())
            return {
                "success": True,
                "symptoms": symptoms,
                "count": len(symptoms),
                "source": "fallback",
                "warning": "Database query failed, using fallback data"
            }
        except:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get symptoms database: {str(e)}"
            )

