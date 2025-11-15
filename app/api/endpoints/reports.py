"""
Reports API Endpoints
Handles reports for SuperAdmin
"""

from datetime import date, timedelta, datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_async_session
from app.models import (
    Clinic, User, UserRole, Patient, Appointment,
    Invoice, Payment, InvoiceStatus, PaymentStatus
)
from app.middleware.permissions import require_super_admin
from app.models.license import License, LicenseStatus

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/active-clients")
async def get_active_clients_report(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_super_admin()),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get active clients report (SuperAdmin only)
    Returns list of active clinics with statistics
    """
    try:
        # Base query for active clinics
        query = select(Clinic).filter(Clinic.is_active == True)
        
        # Apply search filter
        if search:
            search_filter = or_(
                Clinic.name.ilike(f"%{search}%"),
                Clinic.legal_name.ilike(f"%{search}%"),
                Clinic.tax_id.ilike(f"%{search}%"),
                Clinic.email.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Order by name
        query = query.order_by(Clinic.name).offset(skip).limit(limit)
        
        result = await db.execute(query)
        clinics = result.scalars().all()
    except Exception as e:
        # Rollback on error
        await db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching clinics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching clinics: {str(e)}"
        )
    
    # Build response with statistics for each clinic
    clients = []
    for clinic in clinics:
        try:
            # Count active users
            try:
                users_query = select(func.count(User.id)).filter(
                    and_(
                        User.clinic_id == clinic.id,
                        User.is_active == True
                    )
                )
                users_result = await db.execute(users_query)
                user_count = users_result.scalar() or 0
            except Exception as e:
                # If there's an error counting users, rollback and default to 0
                await db.rollback()
                user_count = 0
            
            # Get license information
            license_info = None
            if clinic.license_id:
                try:
                    license_query = select(License).filter(License.id == clinic.license_id)
                    license_result = await db.execute(license_query)
                    license_obj = license_result.scalar_one_or_none()
                    if license_obj:
                        license_info = {
                            "plan": license_obj.plan.value if hasattr(license_obj.plan, 'value') else str(license_obj.plan),
                            "status": license_obj.status.value if hasattr(license_obj.status, 'value') else str(license_obj.status),
                            "end_at": license_obj.end_at.isoformat() if license_obj.end_at else None,
                        }
                except Exception as e:
                    # If there's an error getting license info, rollback and skip it
                    await db.rollback()
                    license_info = None
            
            # Calculate revenue (from paid invoices in the last 30 days)
            try:
                thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
                revenue_query = select(func.coalesce(func.sum(Payment.amount), 0)).join(
                    Invoice, Payment.invoice_id == Invoice.id
                ).filter(
                    and_(
                        Invoice.clinic_id == clinic.id,
                        Payment.status == PaymentStatus.COMPLETED,
                        Payment.created_at >= thirty_days_ago
                    )
                )
                revenue_result = await db.execute(revenue_query)
                revenue_value = revenue_result.scalar()
                revenue = float(revenue_value) if revenue_value is not None else 0.0
            except Exception as e:
                # If there's an error calculating revenue, rollback and default to 0
                await db.rollback()
                revenue = 0.0
            
            # Get last activity (most recent appointment or invoice)
            try:
                last_appointment_query = select(func.max(Appointment.scheduled_datetime)).filter(
                    Appointment.clinic_id == clinic.id
                )
                last_appointment_result = await db.execute(last_appointment_query)
                last_appointment = last_appointment_result.scalar()
                
                last_invoice_query = select(func.max(Invoice.created_at)).filter(
                    Invoice.clinic_id == clinic.id
                )
                last_invoice_result = await db.execute(last_invoice_query)
                last_invoice = last_invoice_result.scalar()
                
                # Determine last activity
                last_activity = None
                if last_appointment and last_invoice:
                    last_activity = max(last_appointment, last_invoice)
                elif last_appointment:
                    last_activity = last_appointment
                elif last_invoice:
                    last_activity = last_invoice
            except Exception as e:
                # If there's an error getting last activity, rollback and set to None
                await db.rollback()
                last_activity = None
        
            clients.append({
                "id": clinic.id,
                "name": clinic.name,
                "legal_name": clinic.legal_name,
                "tax_id": clinic.tax_id,
                "email": clinic.email,
                "license_type": license_info["plan"] if license_info else "N/A",
                "license_status": license_info["status"] if license_info else "N/A",
                "users": user_count,
                "max_users": clinic.max_users,
                "status": "Ativo" if clinic.is_active else "Inativo",
                "last_activity": last_activity.isoformat() if last_activity else None,
                "revenue": revenue,
                "created_at": clinic.created_at.isoformat() if clinic.created_at else None,
            })
        except Exception as e:
            # If there's an error processing a clinic, rollback, log it and continue with next clinic
            await db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing clinic {clinic.id}: {str(e)}", exc_info=True)
            # Continue to next clinic instead of failing the entire request
            continue
    
    return {
        "total": len(clients),
        "clients": clients
    }


@router.get("/active-clients/stats")
async def get_active_clients_stats(
    current_user: User = Depends(require_super_admin()),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get active clients statistics (SuperAdmin only)
    """
    # Total active clinics
    total_clinics_query = select(func.count(Clinic.id)).filter(Clinic.is_active == True)
    total_result = await db.execute(total_clinics_query)
    total_clinics = total_result.scalar() or 0
    
    # Total active users across all clinics
    total_users_query = select(func.count(User.id)).filter(
        and_(
            User.is_active == True,
            User.clinic_id.in_(
                select(Clinic.id).filter(Clinic.is_active == True)
            )
        )
    )
    users_result = await db.execute(total_users_query)
    total_users = users_result.scalar() or 0
    
    # Total revenue (from paid invoices in the last 30 days)
    try:
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        revenue_query = select(func.coalesce(func.sum(Payment.amount), 0)).join(
            Invoice, Payment.invoice_id == Invoice.id
        ).join(
            Clinic, Invoice.clinic_id == Clinic.id
        ).filter(
            and_(
                Clinic.is_active == True,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.created_at >= thirty_days_ago
            )
        )
        revenue_result = await db.execute(revenue_query)
        revenue_value = revenue_result.scalar()
        total_revenue = float(revenue_value) if revenue_value is not None else 0.0
    except Exception as e:
        # If there's an error calculating revenue, default to 0
        total_revenue = 0.0
    
    # Calculate active percentage (all active clinics / all clinics)
    all_clinics_query = select(func.count(Clinic.id))
    all_clinics_result = await db.execute(all_clinics_query)
    all_clinics = all_clinics_result.scalar() or 1  # Avoid division by zero
    active_percentage = (total_clinics / all_clinics * 100) if all_clinics > 0 else 0
    
    return {
        "total_clients": total_clinics,
        "active_clients": total_clinics,  # All are active in this report
        "total_users": total_users,
        "total_revenue": total_revenue,
        "active_percentage": round(active_percentage, 1)
    }

