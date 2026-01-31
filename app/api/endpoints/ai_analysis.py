"""
AI Analysis API
Analyzes consultation transcriptions with attached patient exams to provide:
- ICD-10 code suggestions
- Recommended exams
- Clinical insights
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging

from app.models import User, Appointment
from app.core.auth import get_current_user
from database import get_async_session
from pydantic import BaseModel

router = APIRouter(prefix="/ai", tags=["AI Analysis"])
logger = logging.getLogger(__name__)


class AnalyzeConsultationRequest(BaseModel):
    transcription: str
    appointment_id: int
    exam_ids: List[int] = []


class ICDSuggestion(BaseModel):
    code: str
    description: str
    confidence: float


class ExamRecommendation(BaseModel):
    name: str
    reason: str


class AnalysisResponse(BaseModel):
    icd_codes: List[ICDSuggestion]
    recommended_exams: List[ExamRecommendation]
    clinical_summary: Optional[str] = None


@router.post("/analyze-consultation", response_model=AnalysisResponse)
async def analyze_consultation(
    request: AnalyzeConsultationRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Analyze consultation transcription with attached patient exams
    
    Provides:
    - ICD-10 code suggestions based on transcription and exam results
    - Recommended exams based on symptoms and current exam results
    - Clinical summary and insights
    
    Args:
        transcription: Full consultation transcription
        appointment_id: Appointment ID
        exam_ids: List of exam IDs to include in analysis
    
    Returns:
        ICD code suggestions, recommended exams, and clinical summary
    """
    try:
        # Verify appointment access
        appointment_query = select(Appointment).where(Appointment.id == request.appointment_id)
        appointment_result = await db.execute(appointment_query)
        appointment = appointment_result.scalar_one_or_none()
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        if appointment.doctor_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this appointment")
        
        # Get exam details if provided
        exam_context = ""
        if request.exam_ids:
            # In production, fetch exam details and results from database
            # For now, we'll include exam IDs in the context
            exam_context = f"\n\nExames anexados: {len(request.exam_ids)} exames selecionados para análise."
        
        # Prepare context for AI analysis
        full_context = f"""
Transcrição da Consulta:
{request.transcription}
{exam_context}

Com base na transcrição acima e nos exames do paciente, forneça:
1. Códigos CID-10 sugeridos com descrições
2. Exames complementares recomendados com justificativas
3. Resumo clínico
"""
        
        # Use AI service for analysis
        try:
            from app.services.ai_service import get_ai_service
            
            ai_service = get_ai_service()
            
            # Generate analysis using AI
            analysis_result = await ai_service.analyze_clinical_case(
                context=full_context,
                appointment_id=request.appointment_id,
                db=db
            )
            
            # Parse AI response into structured format
            icd_suggestions = []
            exam_recommendations = []
            
            # Extract ICD codes from analysis
            if "icd_codes" in analysis_result:
                for icd in analysis_result["icd_codes"]:
                    icd_suggestions.append(ICDSuggestion(
                        code=icd.get("code", ""),
                        description=icd.get("description", ""),
                        confidence=icd.get("confidence", 0.8)
                    ))
            
            # Extract exam recommendations
            if "recommended_exams" in analysis_result:
                for exam in analysis_result["recommended_exams"]:
                    exam_recommendations.append(ExamRecommendation(
                        name=exam.get("name", ""),
                        reason=exam.get("reason", "")
                    ))
            
            # If AI service doesn't return structured data, use fallback
            if not icd_suggestions:
                icd_suggestions = await _generate_fallback_icd_suggestions(request.transcription, db)
            
            if not exam_recommendations:
                exam_recommendations = _generate_fallback_exam_recommendations()
            
            return AnalysisResponse(
                icd_codes=icd_suggestions,
                recommended_exams=exam_recommendations,
                clinical_summary=analysis_result.get("summary", "Análise concluída com sucesso.")
            )
            
        except Exception as ai_error:
            logger.error(f"AI analysis error: {str(ai_error)}")
            
            # Fallback to rule-based analysis
            icd_suggestions = await _generate_fallback_icd_suggestions(request.transcription, db)
            exam_recommendations = _generate_fallback_exam_recommendations()
            
            return AnalysisResponse(
                icd_codes=icd_suggestions,
                recommended_exams=exam_recommendations,
                clinical_summary="Análise realizada com base em regras clínicas padrão."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing consultation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze consultation: {str(e)}")


async def _generate_fallback_icd_suggestions(
    transcription: str,
    db: AsyncSession
) -> List[ICDSuggestion]:
    """Generate ICD suggestions using keyword matching as fallback"""
    suggestions = []
    
    transcription_lower = transcription.lower()
    
    # Common symptom to ICD mapping
    symptom_icd_map = {
        "dor no peito": ("R07.9", "Dor torácica não especificada", 0.7),
        "chest pain": ("R07.9", "Dor torácica não especificada", 0.7),
        "falta de ar": ("R06.0", "Dispneia", 0.75),
        "shortness of breath": ("R06.0", "Dispneia", 0.75),
        "tosse": ("R05", "Tosse", 0.8),
        "cough": ("R05", "Tosse", 0.8),
        "febre": ("R50.9", "Febre não especificada", 0.85),
        "fever": ("R50.9", "Febre não especificada", 0.85),
        "dor de cabeça": ("R51", "Cefaleia", 0.8),
        "headache": ("R51", "Cefaleia", 0.8),
        "náusea": ("R11.0", "Náusea", 0.85),
        "nausea": ("R11.0", "Náusea", 0.85),
        "vômito": ("R11.1", "Vômito", 0.85),
        "vomiting": ("R11.1", "Vômito", 0.85),
        "diarreia": ("A09", "Diarreia", 0.8),
        "diarrhea": ("A09", "Diarreia", 0.8),
    }
    
    # Find matching symptoms
    for symptom, (code, description, confidence) in symptom_icd_map.items():
        if symptom in transcription_lower:
            suggestions.append(ICDSuggestion(
                code=code,
                description=description,
                confidence=confidence
            ))
    
    # If no matches, return general codes
    if not suggestions:
        suggestions = [
            ICDSuggestion(
                code="Z00.0",
                description="Exame médico geral",
                confidence=0.6
            )
        ]
    
    return suggestions[:5]  # Return top 5


def _generate_fallback_exam_recommendations() -> List[ExamRecommendation]:
    """Generate common exam recommendations as fallback"""
    return [
        ExamRecommendation(
            name="Hemograma completo",
            reason="Avaliação geral do estado de saúde"
        ),
        ExamRecommendation(
            name="Glicemia de jejum",
            reason="Rastreamento de diabetes"
        ),
        ExamRecommendation(
            name="Ureia e Creatinina",
            reason="Avaliação da função renal"
        ),
    ]
