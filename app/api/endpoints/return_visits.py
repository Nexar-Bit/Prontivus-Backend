"""
Return Visit Management API
Manages return visit configurations, validations, and approvals
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import logging

from app.models import User
from app.models.return_visit_config import ReturnVisitConfig, ReturnVisitApproval
from app.core.auth import get_current_user
from app.services.return_visit_service import return_visit_service
from database import get_async_session

router = APIRouter(prefix="/return-visits", tags=["Return Visits"])
logger = logging.getLogger(__name__)


# Schemas
class ReturnVisitConfigCreate(BaseModel):
    doctor_id: int
    enable_return_limit: bool = True
    return_window_days: int = 30
    daily_return_limit: int = 5
    monthly_return_limit: Optional[int] = None
    require_approval_when_exceeded: bool = True
    approval_message: Optional[str] = None


class ReturnVisitConfigUpdate(BaseModel):
    enable_return_limit: Optional[bool] = None
    return_window_days: Optional[int] = None
    daily_return_limit: Optional[int] = None
    monthly_return_limit: Optional[int] = None
    require_approval_when_exceeded: Optional[bool] = None
    approval_message: Optional[str] = None


class ReturnVisitConfigResponse(BaseModel):
    id: int
    doctor_id: int
    enable_return_limit: bool
    return_window_days: int
    daily_return_limit: int
    monthly_return_limit: Optional[int]
    require_approval_when_exceeded: bool
    approval_message: Optional[str]
    
    class Config:
        from_attributes = True


class ValidateReturnVisitRequest(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_date: str  # ISO format


class ApprovalRequest(BaseModel):
    appointment_id: int
    patient_id: int
    doctor_id: int
    reason: str


class ApprovalActionRequest(BaseModel):
    notes: Optional[str] = None


# Endpoints
@router.post("/configs", response_model=ReturnVisitConfigResponse)
async def create_return_visit_config(
    config: ReturnVisitConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Create or update return visit configuration for a doctor"""
    try:
        # Check if config already exists
        existing_query = select(ReturnVisitConfig).where(
            and_(
                ReturnVisitConfig.doctor_id == config.doctor_id,
                ReturnVisitConfig.clinic_id == current_user.clinic_id
            )
        )
        existing_result = await db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            # Update existing
            for key, value in config.dict(exclude_unset=True).items():
                if key != "doctor_id":
                    setattr(existing, key, value)
            
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            # Create new
            new_config = ReturnVisitConfig(
                **config.dict(),
                clinic_id=current_user.clinic_id
            )
            db.add(new_config)
            await db.commit()
            await db.refresh(new_config)
            return new_config
            
    except Exception as e:
        logger.error(f"Error creating return visit config: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{doctor_id}", response_model=ReturnVisitConfigResponse)
async def get_return_visit_config(
    doctor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get return visit configuration for a doctor"""
    try:
        query = select(ReturnVisitConfig).where(
            and_(
                ReturnVisitConfig.doctor_id == doctor_id,
                ReturnVisitConfig.clinic_id == current_user.clinic_id
            )
        )
        result = await db.execute(query)
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting return visit config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_return_visit(
    request: ValidateReturnVisitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Validate if appointment is a return visit and check limits
    
    Returns validation result with approval requirements if needed
    """
    try:
        appointment_date = datetime.fromisoformat(request.appointment_date)
        
        validation = await return_visit_service.validate_return_visit(
            db=db,
            patient_id=request.patient_id,
            doctor_id=request.doctor_id,
            clinic_id=current_user.clinic_id,
            appointment_date=appointment_date
        )
        
        return validation
        
    except Exception as e:
        logger.error(f"Error validating return visit: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approvals")
async def create_approval_request(
    request: ApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Create an approval request for a return visit that exceeds limits"""
    try:
        approval = await return_visit_service.create_approval_request(
            db=db,
            appointment_id=request.appointment_id,
            patient_id=request.patient_id,
            doctor_id=request.doctor_id,
            clinic_id=current_user.clinic_id,
            requested_by=current_user.id,
            reason=request.reason
        )
        
        return {
            "success": True,
            "approval_id": approval.id,
            "status": approval.status,
            "message": "Solicitação de aprovação criada com sucesso"
        }
        
    except Exception as e:
        logger.error(f"Error creating approval request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approvals/{approval_id}/approve")
async def approve_return_visit(
    approval_id: int,
    request: ApprovalActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Approve a return visit request (doctor only)"""
    try:
        approval = await return_visit_service.approve_return_visit(
            db=db,
            approval_id=approval_id,
            approved_by=current_user.id,
            notes=request.notes
        )
        
        return {
            "success": True,
            "approval_id": approval.id,
            "status": approval.status,
            "message": "Retorno aprovado com sucesso"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving return visit: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approvals/{approval_id}/reject")
async def reject_return_visit(
    approval_id: int,
    request: ApprovalActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Reject a return visit request (doctor only)"""
    try:
        approval = await return_visit_service.reject_return_visit(
            db=db,
            approval_id=approval_id,
            rejected_by=current_user.id,
            notes=request.notes
        )
        
        return {
            "success": True,
            "approval_id": approval.id,
            "status": approval.status,
            "message": "Retorno rejeitado"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rejecting return visit: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approvals/pending")
async def get_pending_approvals(
    doctor_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get pending approval requests"""
    try:
        query = select(ReturnVisitApproval).where(
            and_(
                ReturnVisitApproval.clinic_id == current_user.clinic_id,
                ReturnVisitApproval.status == "pending"
            )
        )
        
        if doctor_id:
            query = query.where(ReturnVisitApproval.doctor_id == doctor_id)
        
        result = await db.execute(query)
        approvals = result.scalars().all()
        
        return {
            "success": True,
            "count": len(approvals),
            "approvals": [
                {
                    "id": approval.id,
                    "appointment_id": approval.appointment_id,
                    "patient_id": approval.patient_id,
                    "doctor_id": approval.doctor_id,
                    "requested_by": approval.requested_by,
                    "reason": approval.reason,
                    "status": approval.status,
                    "created_at": approval.created_at.isoformat()
                }
                for approval in approvals
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting pending approvals: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggest-dates")
async def get_suggested_dates(
    patient_id: int = Body(...),
    doctor_id: int = Body(...),
    start_date: str = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get suggested appointment dates considering return visit rules"""
    try:
        start_datetime = datetime.fromisoformat(start_date)
        
        suggestions = await return_visit_service.get_suggested_dates(
            db=db,
            patient_id=patient_id,
            doctor_id=doctor_id,
            clinic_id=current_user.clinic_id,
            start_date=start_datetime,
            days_ahead=14
        )
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Error getting suggested dates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
