"""
Return Visit Service
Manages return visit validation, limits, and approval workflows
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_

from app.models import Appointment, User
from app.models.return_visit_config import ReturnVisitConfig, ReturnVisitApproval

logger = logging.getLogger(__name__)


class ReturnVisitService:
    """Service for managing return visit policies and validations"""
    
    @staticmethod
    async def validate_return_visit(
        db: AsyncSession,
        patient_id: int,
        doctor_id: int,
        clinic_id: int,
        appointment_date: datetime
    ) -> Dict:
        """
        Validate if appointment qualifies as return visit and check limits
        
        Returns:
            {
                "is_return_visit": bool,
                "last_visit_date": datetime or None,
                "days_since_last_visit": int or None,
                "requires_approval": bool,
                "approval_reason": str or None,
                "daily_limit_reached": bool,
                "monthly_limit_reached": bool,
                "allowed": bool
            }
        """
        try:
            # Get doctor's return visit configuration
            config_query = select(ReturnVisitConfig).where(
                and_(
                    ReturnVisitConfig.doctor_id == doctor_id,
                    ReturnVisitConfig.clinic_id == clinic_id
                )
            )
            config_result = await db.execute(config_query)
            config = config_result.scalar_one_or_none()
            
            # If no config, allow by default
            if not config or not config.enable_return_limit:
                return {
                    "is_return_visit": False,
                    "last_visit_date": None,
                    "days_since_last_visit": None,
                    "requires_approval": False,
                    "approval_reason": None,
                    "daily_limit_reached": False,
                    "monthly_limit_reached": False,
                    "allowed": True
                }
            
            # Check for last visit within return window
            return_window_start = appointment_date - timedelta(days=config.return_window_days)
            
            last_visit_query = select(Appointment).where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.doctor_id == doctor_id,
                    Appointment.clinic_id == clinic_id,
                    Appointment.appointment_date < appointment_date,
                    Appointment.appointment_date >= return_window_start,
                    Appointment.status.in_(["completed", "confirmed", "in_progress"])
                )
            ).order_by(Appointment.appointment_date.desc())
            
            last_visit_result = await db.execute(last_visit_query)
            last_visit = last_visit_result.scalar_one_or_none()
            
            is_return_visit = last_visit is not None
            
            if not is_return_visit:
                return {
                    "is_return_visit": False,
                    "last_visit_date": None,
                    "days_since_last_visit": None,
                    "requires_approval": False,
                    "approval_reason": None,
                    "daily_limit_reached": False,
                    "monthly_limit_reached": False,
                    "allowed": True
                }
            
            days_since_last_visit = (appointment_date - last_visit.appointment_date).days
            
            # Check daily return limit
            day_start = appointment_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            daily_return_count_query = select(func.count(Appointment.id)).where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.clinic_id == clinic_id,
                    Appointment.appointment_date >= day_start,
                    Appointment.appointment_date < day_end,
                    Appointment.id.in_(
                        # Subquery: appointments that are return visits
                        select(Appointment.id).where(
                            and_(
                                Appointment.doctor_id == doctor_id,
                                Appointment.clinic_id == clinic_id,
                                Appointment.appointment_date >= day_start,
                                Appointment.appointment_date < day_end,
                                # Has previous visit in last N days
                                Appointment.patient_id.in_(
                                    select(Appointment.patient_id).where(
                                        and_(
                                            Appointment.doctor_id == doctor_id,
                                            Appointment.appointment_date < appointment_date,
                                            Appointment.appointment_date >= return_window_start
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
            
            daily_return_count_result = await db.execute(daily_return_count_query)
            daily_return_count = daily_return_count_result.scalar() or 0
            
            daily_limit_reached = daily_return_count >= config.daily_return_limit
            
            # Check monthly return limit (if configured)
            monthly_limit_reached = False
            if config.monthly_return_limit:
                month_start = appointment_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                next_month = month_start + timedelta(days=32)
                month_end = next_month.replace(day=1)
                
                monthly_return_count_query = select(func.count(Appointment.id)).where(
                    and_(
                        Appointment.doctor_id == doctor_id,
                        Appointment.clinic_id == clinic_id,
                        Appointment.appointment_date >= month_start,
                        Appointment.appointment_date < month_end
                    )
                )
                
                monthly_return_count_result = await db.execute(monthly_return_count_query)
                monthly_return_count = monthly_return_count_result.scalar() or 0
                
                monthly_limit_reached = monthly_return_count >= config.monthly_return_limit
            
            # Determine if approval is required
            requires_approval = False
            approval_reason = None
            
            if daily_limit_reached or monthly_limit_reached:
                requires_approval = config.require_approval_when_exceeded
                
                if daily_limit_reached:
                    approval_reason = f"Limite diário de retornos atingido ({config.daily_return_limit})"
                elif monthly_limit_reached:
                    approval_reason = f"Limite mensal de retornos atingido ({config.monthly_return_limit})"
            
            allowed = not (daily_limit_reached or monthly_limit_reached) or not requires_approval
            
            return {
                "is_return_visit": True,
                "last_visit_date": last_visit.appointment_date,
                "days_since_last_visit": days_since_last_visit,
                "requires_approval": requires_approval,
                "approval_reason": approval_reason,
                "daily_limit_reached": daily_limit_reached,
                "monthly_limit_reached": monthly_limit_reached,
                "allowed": allowed,
                "daily_return_count": daily_return_count,
                "daily_return_limit": config.daily_return_limit
            }
            
        except Exception as e:
            logger.error(f"Error validating return visit: {str(e)}", exc_info=True)
            # On error, allow by default (fail open)
            return {
                "is_return_visit": False,
                "last_visit_date": None,
                "days_since_last_visit": None,
                "requires_approval": False,
                "approval_reason": None,
                "daily_limit_reached": False,
                "monthly_limit_reached": False,
                "allowed": True,
                "error": str(e)
            }
    
    @staticmethod
    async def create_approval_request(
        db: AsyncSession,
        appointment_id: int,
        patient_id: int,
        doctor_id: int,
        clinic_id: int,
        requested_by: int,
        reason: str
    ) -> ReturnVisitApproval:
        """Create an approval request for a return visit that exceeds limits"""
        try:
            approval = ReturnVisitApproval(
                clinic_id=clinic_id,
                appointment_id=appointment_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                requested_by=requested_by,
                reason=reason,
                status="pending"
            )
            
            db.add(approval)
            await db.commit()
            await db.refresh(approval)
            
            logger.info(f"Created return visit approval request: {approval.id}")
            
            # TODO: Send notification to doctor
            
            return approval
            
        except Exception as e:
            logger.error(f"Error creating approval request: {str(e)}", exc_info=True)
            await db.rollback()
            raise
    
    @staticmethod
    async def approve_return_visit(
        db: AsyncSession,
        approval_id: int,
        approved_by: int,
        notes: Optional[str] = None
    ) -> ReturnVisitApproval:
        """Approve a return visit request"""
        try:
            approval_query = select(ReturnVisitApproval).where(
                ReturnVisitApproval.id == approval_id
            )
            approval_result = await db.execute(approval_query)
            approval = approval_result.scalar_one_or_none()
            
            if not approval:
                raise ValueError("Approval request not found")
            
            if approval.status != "pending":
                raise ValueError("Approval request already processed")
            
            approval.status = "approved"
            approval.approved_by = approved_by
            approval.approval_notes = notes
            approval.approved_at = datetime.now()
            
            await db.commit()
            await db.refresh(approval)
            
            logger.info(f"Approved return visit: {approval.id}")
            
            # TODO: Send notification to secretary
            
            return approval
            
        except Exception as e:
            logger.error(f"Error approving return visit: {str(e)}", exc_info=True)
            await db.rollback()
            raise
    
    @staticmethod
    async def reject_return_visit(
        db: AsyncSession,
        approval_id: int,
        rejected_by: int,
        notes: Optional[str] = None
    ) -> ReturnVisitApproval:
        """Reject a return visit request"""
        try:
            approval_query = select(ReturnVisitApproval).where(
                ReturnVisitApproval.id == approval_id
            )
            approval_result = await db.execute(approval_query)
            approval = approval_result.scalar_one_or_none()
            
            if not approval:
                raise ValueError("Approval request not found")
            
            if approval.status != "pending":
                raise ValueError("Approval request already processed")
            
            approval.status = "rejected"
            approval.approved_by = rejected_by
            approval.approval_notes = notes
            approval.approved_at = datetime.now()
            
            await db.commit()
            await db.refresh(approval)
            
            logger.info(f"Rejected return visit: {approval.id}")
            
            # TODO: Send notification to secretary
            # TODO: Cancel or update appointment
            
            return approval
            
        except Exception as e:
            logger.error(f"Error rejecting return visit: {str(e)}", exc_info=True)
            await db.rollback()
            raise
    
    @staticmethod
    async def get_suggested_dates(
        db: AsyncSession,
        patient_id: int,
        doctor_id: int,
        clinic_id: int,
        start_date: datetime,
        days_ahead: int = 14
    ) -> Dict:
        """
        Suggest available appointment dates considering return visit rules
        
        Returns dates that won't trigger return visit limits
        """
        try:
            # Get doctor's return visit configuration
            config_query = select(ReturnVisitConfig).where(
                and_(
                    ReturnVisitConfig.doctor_id == doctor_id,
                    ReturnVisitConfig.clinic_id == clinic_id
                )
            )
            config_result = await db.execute(config_query)
            config = config_result.scalar_one_or_none()
            
            # Get last visit
            last_visit_query = select(Appointment).where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.doctor_id == doctor_id,
                    Appointment.clinic_id == clinic_id,
                    Appointment.appointment_date < start_date,
                    Appointment.status.in_(["completed", "confirmed"])
                )
            ).order_by(Appointment.appointment_date.desc())
            
            last_visit_result = await db.execute(last_visit_query)
            last_visit = last_visit_result.scalar_one_or_none()
            
            suggested_dates = []
            
            if not config or not last_visit:
                # No restrictions
                return {
                    "has_restrictions": False,
                    "suggested_dates": [],
                    "message": "Sem restrições de retorno"
                }
            
            # Calculate dates outside return window
            return_window_end = last_visit.appointment_date + timedelta(days=config.return_window_days)
            
            if start_date < return_window_end:
                # Suggest dates after return window
                for i in range(7):  # Suggest next 7 days after window
                    suggested_date = return_window_end + timedelta(days=i)
                    suggested_dates.append(suggested_date.isoformat())
            
            return {
                "has_restrictions": len(suggested_dates) > 0,
                "last_visit_date": last_visit.appointment_date.isoformat(),
                "return_window_days": config.return_window_days,
                "return_window_ends": return_window_end.isoformat(),
                "suggested_dates": suggested_dates,
                "message": f"Paciente teve consulta recente. Sugerimos agendar após {return_window_end.strftime('%d/%m/%Y')}"
            }
            
        except Exception as e:
            logger.error(f"Error getting suggested dates: {str(e)}", exc_info=True)
            return {
                "has_restrictions": False,
                "suggested_dates": [],
                "error": str(e)
            }


# Global service instance
return_visit_service = ReturnVisitService()
