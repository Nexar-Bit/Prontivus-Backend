"""
TISS SP/SADT Guide Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel

from database import get_async_session
from app.models import User
from app.core.auth import get_current_user, RoleChecker, UserRole
from app.models.tiss.sadt import TISSSADTGuide
from app.services.tiss.sadt_form import SADTFormService
from app.services.tiss.xsd_validator import XSDValidator
from app.services.tiss.versioning import TISSVersioningService

router = APIRouter(prefix="/tiss/sadt", tags=["TISS SADT"])

require_doctor = RoleChecker([UserRole.DOCTOR, UserRole.ADMIN])


class SADTGuideCreate(BaseModel):
    invoice_id: int
    prestador: dict
    operadora: dict
    beneficiario: dict
    contratado: dict
    sadt: dict
    valor_total: float


class SADTGuideResponse(BaseModel):
    id: int
    numero_guia: str
    status: str
    valor_total: float
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/", response_model=SADTGuideResponse, status_code=status.HTTP_201_CREATED)
async def create_sadt_guide(
    guide_data: SADTGuideCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new SP/SADT guide"""
    service = SADTFormService(db)
    
    guide = await service.create_sadt_guide(
        invoice_id=guide_data.invoice_id,
        clinic_id=current_user.clinic_id,
        user_id=current_user.id,
        guide_data=guide_data.dict()
    )
    
    return SADTGuideResponse(
        id=guide.id,
        numero_guia=guide.numero_guia,
        status=guide.status,
        valor_total=float(guide.valor_total),
        created_at=guide.created_at.isoformat()
    )


@router.get("/{guide_id}", response_model=SADTGuideResponse)
async def get_sadt_guide(
    guide_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get a SP/SADT guide by ID"""
    query = select(TISSSADTGuide).where(
        TISSSADTGuide.id == guide_id,
        TISSSADTGuide.clinic_id == current_user.clinic_id
    )
    result = await db.execute(query)
    guide = result.scalar_one_or_none()
    
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found")
    
    return SADTGuideResponse(
        id=guide.id,
        numero_guia=guide.numero_guia,
        status=guide.status,
        valor_total=float(guide.valor_total),
        created_at=guide.created_at.isoformat()
    )


@router.post("/{guide_id}/validate")
async def validate_sadt_guide(
    guide_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Validate a SP/SADT guide"""
    service = SADTFormService(db)
    result = await service.validate_sadt_guide(guide_id)
    return result


@router.post("/{guide_id}/generate-xml")
async def generate_xml(
    guide_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Generate XML for a SP/SADT guide"""
    service = SADTFormService(db)
    xml_content = await service.generate_xml(guide_id)
    return {"xml": xml_content}


@router.post("/{guide_id}/validate-xml")
async def validate_xml(
    guide_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Validate XML against XSD schema"""
    query = select(TISSSADTGuide).where(
        TISSSADTGuide.id == guide_id,
        TISSSADTGuide.clinic_id == current_user.clinic_id
    )
    result = await db.execute(query)
    guide = result.scalar_one_or_none()
    
    if not guide or not guide.xml_content:
        raise HTTPException(status_code=404, detail="Guide or XML not found")
    
    versioning = TISSVersioningService(db)
    validator = XSDValidator(versioning)
    validation_result = await validator.validate_xml(guide.xml_content, guide.versao_tiss)
    
    return validation_result


@router.post("/{guide_id}/lock")
async def lock_guide(
    guide_id: int,
    current_user: User = Depends(require_doctor),
    db: AsyncSession = Depends(get_async_session)
):
    """Lock guide to prevent editing after submission"""
    service = SADTFormService(db)
    await service.lock_guide(guide_id, current_user.id)
    return {"message": "Guide locked successfully"}

