"""
TISS Batch Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from database import get_async_session
from app.models import User
from app.core.auth import get_current_user, RoleChecker, UserRole
from app.models.tiss.batch import TISSBatch
from app.services.tiss.batch_generator import BatchGeneratorService

router = APIRouter(prefix="/tiss/batch", tags=["TISS Batch"])

require_doctor = RoleChecker([UserRole.DOCTOR, UserRole.ADMIN])


class BatchCreate(BaseModel):
    guide_ids: List[int]
    guide_type: str  # 'consultation', 'sadt', 'hospitalization', 'individual_fee'


class BatchResponse(BaseModel):
    id: int
    numero_lote: str
    submission_status: str
    valor_total_lote: float
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    batch_data: BatchCreate,
    current_user: User = Depends(require_doctor),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new TISS batch"""
    service = BatchGeneratorService(db)
    
    batch = await service.create_batch(
        clinic_id=current_user.clinic_id,
        guide_ids=batch_data.guide_ids,
        guide_type=batch_data.guide_type
    )
    
    return BatchResponse(
        id=batch.id,
        numero_lote=batch.numero_lote,
        submission_status=batch.submission_status,
        valor_total_lote=float(batch.valor_total_lote) if batch.valor_total_lote else 0.0,
        created_at=batch.created_at.isoformat()
    )


@router.post("/{batch_id}/generate-xml")
async def generate_batch_xml(
    batch_id: int,
    current_user: User = Depends(require_doctor),
    db: AsyncSession = Depends(get_async_session)
):
    """Generate XML for a batch"""
    from sqlalchemy import select
    
    query = select(TISSBatch).where(
        TISSBatch.id == batch_id,
        TISSBatch.clinic_id == current_user.clinic_id
    )
    result = await db.execute(query)
    batch = result.scalar_one_or_none()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    service = BatchGeneratorService(db)
    xml_content = await service.generate_batch_xml(batch_id)
    
    return {"xml": xml_content}


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get a batch by ID"""
    from sqlalchemy import select
    
    query = select(TISSBatch).where(
        TISSBatch.id == batch_id,
        TISSBatch.clinic_id == current_user.clinic_id
    )
    result = await db.execute(query)
    batch = result.scalar_one_or_none()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return BatchResponse(
        id=batch.id,
        numero_lote=batch.numero_lote,
        submission_status=batch.submission_status,
        valor_total_lote=float(batch.valor_total_lote) if batch.valor_total_lote else 0.0,
        created_at=batch.created_at.isoformat()
    )

