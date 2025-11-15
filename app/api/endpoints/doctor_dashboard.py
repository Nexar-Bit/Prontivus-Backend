"""
Doctor Dashboard API Endpoints
Provides aggregated data for doctor dashboard
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import joinedload, selectinload

from app.core.auth import get_current_user
from app.models import User, Patient, Appointment, AppointmentStatus, UserRole
from app.models.clinical import ClinicalRecord, Prescription, ExamRequest
from app.models.financial import Invoice, Payment, InvoiceStatus, PaymentStatus
from database import get_async_session
from pydantic import BaseModel

router = APIRouter(prefix="/doctor", tags=["Doctor Dashboard"])


# ==================== Response Models ====================

class DoctorDashboardStats(BaseModel):
    """Doctor dashboard statistics"""
    today_appointments_count: int
    queue_patients_count: int
    pending_records_count: int
    monthly_revenue: float
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class UpcomingAppointmentResponse(BaseModel):
    """Upcoming appointment response"""
    id: int
    patient_name: str
    scheduled_datetime: datetime
    appointment_type: Optional[str]
    status: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class DoctorDashboardResponse(BaseModel):
    """Doctor dashboard response"""
    stats: DoctorDashboardStats
    upcoming_appointments: List[UpcomingAppointmentResponse]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# ==================== Helper Functions ====================

def make_aware(dt):
    """Make datetime timezone-aware if needed"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ==================== Dashboard Endpoint ====================

@router.get("/dashboard", response_model=DoctorDashboardResponse)
async def get_doctor_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get comprehensive doctor dashboard data
    
    Returns:
    - Statistics (counts of appointments, queue, pending records, revenue)
    - Upcoming appointments for today
    """
    try:
        # Verify user is a doctor
        if current_user.role != UserRole.DOCTOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint is only available for doctors"
            )
        
        # Use timezone-aware datetime to avoid comparison errors
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Month start for revenue calculation
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # ==================== Get Today's Appointments ====================
        today_appointments_query = select(Appointment, Patient).join(
            Patient, Appointment.patient_id == Patient.id
        ).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.scheduled_datetime >= today_start,
                Appointment.scheduled_datetime < today_end
            )
        ).order_by(Appointment.scheduled_datetime)
        
        appointments_result = await db.execute(today_appointments_query)
        appointments_data = appointments_result.all()
        
        today_appointments_count = len(appointments_data)
        
        # ==================== Get Queue Patients (Checked In or In Consultation) ====================
        queue_query = select(func.count(Appointment.id)).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.status.in_([
                    AppointmentStatus.CHECKED_IN,
                    AppointmentStatus.IN_CONSULTATION
                ])
            )
        )
        queue_result = await db.execute(queue_query)
        queue_patients_count = queue_result.scalar() or 0
        
        # ==================== Get Pending Clinical Records ====================
        # Count appointments with clinical records that are incomplete
        # This is a simplified check - you might want to add a status field to ClinicalRecord
        pending_records_query = select(func.count(ClinicalRecord.id)).join(
            Appointment, ClinicalRecord.appointment_id == Appointment.id
        ).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.status == AppointmentStatus.COMPLETED,
                # Check if record is incomplete (no prescriptions or exam requests)
                # This is a simplified check
            )
        )
        pending_records_result = await db.execute(pending_records_query)
        pending_records_count = pending_records_result.scalar() or 0
        
        # Alternative: Count completed appointments without clinical records
        appointments_without_records_query = select(func.count(Appointment.id)).outerjoin(
            ClinicalRecord, Appointment.id == ClinicalRecord.appointment_id
        ).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.status == AppointmentStatus.COMPLETED,
                ClinicalRecord.id.is_(None)
            )
        )
        appointments_without_records_result = await db.execute(appointments_without_records_query)
        appointments_without_records = appointments_without_records_result.scalar() or 0
        
        # Use the count of appointments without records as pending records
        pending_records_count = appointments_without_records
        
        # ==================== Get Monthly Revenue ====================
        try:
            revenue_query = select(func.coalesce(func.sum(Payment.amount), 0)).join(
                Invoice, Payment.invoice_id == Invoice.id
            ).join(
                Appointment, Invoice.appointment_id == Appointment.id
            ).filter(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.clinic_id == current_user.clinic_id,
                    Payment.status == PaymentStatus.COMPLETED,
                    Payment.created_at >= month_start
                )
            )
            revenue_result = await db.execute(revenue_query)
            revenue_value = revenue_result.scalar()
            monthly_revenue = float(revenue_value) if revenue_value is not None else 0.0
        except Exception as e:
            # If there's an error calculating revenue, default to 0
            monthly_revenue = 0.0
        
        # ==================== Build Upcoming Appointments List ====================
        upcoming_appointments = []
        for appointment, patient in appointments_data:
            apt_datetime = make_aware(appointment.scheduled_datetime)
            if apt_datetime and apt_datetime >= now:
                # Get patient full name
                patient_name = f"{patient.first_name or ''} {patient.last_name or ''}".strip()
                if not patient_name:
                    patient_name = patient.email or "Paciente"
                
                upcoming_appointments.append(UpcomingAppointmentResponse(
                    id=appointment.id,
                    patient_name=patient_name,
                    scheduled_datetime=apt_datetime,
                    appointment_type=appointment.appointment_type,
                    status=appointment.status.value if hasattr(appointment.status, 'value') else str(appointment.status)
                ))
        
        # Sort by scheduled time
        upcoming_appointments.sort(key=lambda x: x.scheduled_datetime)
        
        # ==================== Build Response ====================
        stats = DoctorDashboardStats(
            today_appointments_count=today_appointments_count,
            queue_patients_count=queue_patients_count,
            pending_records_count=pending_records_count,
            monthly_revenue=monthly_revenue
        )
        
        return DoctorDashboardResponse(
            stats=stats,
            upcoming_appointments=upcoming_appointments[:10]  # Limit to 10 most recent
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 403)
        raise
    except Exception as e:
        # Log the error and return a safe response
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_doctor_dashboard: {str(e)}", exc_info=True)
        
        # Return empty dashboard on error to prevent frontend crashes
        return DoctorDashboardResponse(
            stats=DoctorDashboardStats(
                today_appointments_count=0,
                queue_patients_count=0,
                pending_records_count=0,
                monthly_revenue=0.0
            ),
            upcoming_appointments=[]
        )


# ==================== Financial Dashboard Endpoint ====================

class DoctorFinancialStats(BaseModel):
    """Doctor financial statistics"""
    monthly_revenue: float
    monthly_expenses: float
    current_balance: float
    pending_amount: float
    monthly_revenue_change: float  # Percentage change from previous month
    monthly_expenses_change: float  # Percentage change from previous month
    balance_change: float  # Percentage change from previous month
    pending_change: float  # Percentage change from previous month
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class MonthlyFinancialData(BaseModel):
    """Monthly financial data for chart"""
    month: str
    revenue: float
    expenses: float


class DoctorFinancialDashboardResponse(BaseModel):
    """Doctor financial dashboard response"""
    stats: DoctorFinancialStats
    monthly_data: List[MonthlyFinancialData]


@router.get("/financial/dashboard", response_model=DoctorFinancialDashboardResponse)
async def get_doctor_financial_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get comprehensive financial dashboard data for the current doctor
    
    Returns:
    - Financial statistics (revenue, expenses, balance, pending)
    - Monthly data for the last 6 months
    """
    try:
        # Verify user is a doctor
        if current_user.role != UserRole.DOCTOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint is only available for doctors"
            )
        
        now = datetime.now(timezone.utc)
        
        # Current month
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_end = (current_month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        current_month_end = current_month_end.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Previous month
        previous_month_end = current_month_start - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # ==================== Get Current Month Revenue ====================
        current_revenue_query = select(func.coalesce(func.sum(Payment.amount), 0)).join(
            Invoice, Payment.invoice_id == Invoice.id
        ).join(
            Appointment, Invoice.appointment_id == Appointment.id
        ).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.created_at >= current_month_start,
                Payment.created_at <= current_month_end
            )
        )
        current_revenue_result = await db.execute(current_revenue_query)
        current_month_revenue = float(current_revenue_result.scalar() or 0)
        
        # ==================== Get Previous Month Revenue ====================
        previous_revenue_query = select(func.coalesce(func.sum(Payment.amount), 0)).join(
            Invoice, Payment.invoice_id == Invoice.id
        ).join(
            Appointment, Invoice.appointment_id == Appointment.id
        ).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.created_at >= previous_month_start,
                Payment.created_at <= previous_month_end
            )
        )
        previous_revenue_result = await db.execute(previous_revenue_query)
        previous_month_revenue = float(previous_revenue_result.scalar() or 0)
        
        # Calculate revenue change percentage
        revenue_change = 0.0
        if previous_month_revenue > 0:
            revenue_change = ((current_month_revenue - previous_month_revenue) / previous_month_revenue) * 100
        elif current_month_revenue > 0:
            revenue_change = 100.0
        
        # ==================== Get Current Month Expenses ====================
        # For now, expenses are 0 (doctors typically don't have expenses in this system)
        # This can be extended if needed
        current_month_expenses = 0.0
        previous_month_expenses = 0.0
        expenses_change = 0.0
        
        # ==================== Get Current Balance ====================
        # Balance is revenue minus expenses
        current_balance = current_month_revenue - current_month_expenses
        previous_balance = previous_month_revenue - previous_month_expenses
        
        # Calculate balance change percentage
        balance_change = 0.0
        if previous_balance > 0:
            balance_change = ((current_balance - previous_balance) / previous_balance) * 100
        elif current_balance > 0:
            balance_change = 100.0
        
        # ==================== Get Pending Amount ====================
        # Sum of invoices with status PENDING for this doctor
        pending_query = select(func.coalesce(func.sum(Invoice.total_amount), 0)).join(
            Appointment, Invoice.appointment_id == Appointment.id
        ).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Invoice.status == InvoiceStatus.PENDING
            )
        )
        pending_result = await db.execute(pending_query)
        current_pending = float(pending_result.scalar() or 0)
        
        # Get previous month pending
        previous_pending_query = select(func.coalesce(func.sum(Invoice.total_amount), 0)).join(
            Appointment, Invoice.appointment_id == Appointment.id
        ).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Invoice.status == InvoiceStatus.PENDING,
                Invoice.issue_date >= previous_month_start,
                Invoice.issue_date <= previous_month_end
            )
        )
        previous_pending_result = await db.execute(previous_pending_query)
        previous_pending = float(previous_pending_result.scalar() or 0)
        
        # Calculate pending change percentage
        pending_change = 0.0
        if previous_pending > 0:
            pending_change = ((current_pending - previous_pending) / previous_pending) * 100
        elif current_pending > 0:
            pending_change = 100.0
        elif previous_pending > 0 and current_pending == 0:
            pending_change = -100.0
        
        # ==================== Get Monthly Data for Last 6 Months ====================
        monthly_data = []
        for i in range(5, -1, -1):  # Last 6 months (5 months ago to current month)
            month_date = (current_month_start - timedelta(days=30 * i))
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            month_end = month_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Get revenue for this month
            month_revenue_query = select(func.coalesce(func.sum(Payment.amount), 0)).join(
                Invoice, Payment.invoice_id == Invoice.id
            ).join(
                Appointment, Invoice.appointment_id == Appointment.id
            ).filter(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.clinic_id == current_user.clinic_id,
                    Payment.status == PaymentStatus.COMPLETED,
                    Payment.created_at >= month_start,
                    Payment.created_at <= month_end
                )
            )
            month_revenue_result = await db.execute(month_revenue_query)
            month_revenue = float(month_revenue_result.scalar() or 0)
            
            # Expenses are 0 for now
            month_expenses = 0.0
            
            # Format month name
            month_name = month_start.strftime("%b")
            if month_name == "Jan":
                month_name = "Jan"
            elif month_name == "Feb":
                month_name = "Fev"
            elif month_name == "Mar":
                month_name = "Mar"
            elif month_name == "Apr":
                month_name = "Abr"
            elif month_name == "May":
                month_name = "Mai"
            elif month_name == "Jun":
                month_name = "Jun"
            elif month_name == "Jul":
                month_name = "Jul"
            elif month_name == "Aug":
                month_name = "Ago"
            elif month_name == "Sep":
                month_name = "Set"
            elif month_name == "Oct":
                month_name = "Out"
            elif month_name == "Nov":
                month_name = "Nov"
            elif month_name == "Dec":
                month_name = "Dez"
            
            monthly_data.append(MonthlyFinancialData(
                month=month_name,
                revenue=month_revenue,
                expenses=month_expenses
            ))
        
        # ==================== Build Response ====================
        stats = DoctorFinancialStats(
            monthly_revenue=current_month_revenue,
            monthly_expenses=current_month_expenses,
            current_balance=current_balance,
            pending_amount=current_pending,
            monthly_revenue_change=revenue_change,
            monthly_expenses_change=expenses_change,
            balance_change=balance_change,
            pending_change=pending_change
        )
        
        return DoctorFinancialDashboardResponse(
            stats=stats,
            monthly_data=monthly_data
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 403)
        raise
    except Exception as e:
        # Log the error and return a safe response
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_doctor_financial_dashboard: {str(e)}", exc_info=True)
        
        # Return empty dashboard on error
        return DoctorFinancialDashboardResponse(
            stats=DoctorFinancialStats(
                monthly_revenue=0.0,
                monthly_expenses=0.0,
                current_balance=0.0,
                pending_amount=0.0,
                monthly_revenue_change=0.0,
                monthly_expenses_change=0.0,
                balance_change=0.0,
                pending_change=0.0
            ),
            monthly_data=[]
        )


# ==================== Cash Flow Endpoint ====================

class DailyCashFlowData(BaseModel):
    """Daily cash flow data"""
    day: str  # Day number (01, 02, etc.)
    date: str  # Full date (YYYY-MM-DD)
    entrada: float  # Revenue (payments received)
    saida: float  # Expenses (currently 0, can be extended)


class DoctorCashFlowResponse(BaseModel):
    """Doctor cash flow response"""
    total_entrada: float
    total_saida: float
    saldo: float
    daily_data: List[DailyCashFlowData]


@router.get("/financial/cash-flow", response_model=DoctorCashFlowResponse)
async def get_doctor_cash_flow(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    days: int = Query(7, ge=1, le=30, description="Number of days to retrieve (default: 7)"),
):
    """
    Get cash flow data for the current doctor
    
    Returns:
    - Total revenue (entrada) from completed payments
    - Total expenses (saida) - currently 0
    - Balance (saldo)
    - Daily data for the specified number of days
    """
    try:
        # Verify user is a doctor
        if current_user.role != UserRole.DOCTOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint is only available for doctors"
            )
        
        now = datetime.now(timezone.utc)
        
        # Calculate date range
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_date = (end_date - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get all payments in the date range
        payments_query = select(Payment, Invoice, Appointment).join(
            Invoice, Payment.invoice_id == Invoice.id
        ).join(
            Appointment, Invoice.appointment_id == Appointment.id
        ).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.created_at >= start_date,
                Payment.created_at <= end_date
            )
        )
        
        payments_result = await db.execute(payments_query)
        payments_data = payments_result.all()
        
        # Group payments by date
        daily_payments: Dict[str, Dict[str, Any]] = {}
        total_entrada = 0.0
        
        for payment, invoice, appointment in payments_data:
            # Get payment date (use created_at)
            payment_date = payment.created_at.date() if hasattr(payment.created_at, 'date') else payment.created_at
            if isinstance(payment_date, datetime):
                payment_date = payment_date.date()
            
            date_key = payment_date.strftime("%Y-%m-%d")
            day_key = payment_date.strftime("%d")
            
            if date_key not in daily_payments:
                daily_payments[date_key] = {
                    "day": day_key,
                    "entrada": 0.0,
                    "saida": 0.0
                }
            
            amount = float(payment.amount)
            daily_payments[date_key]["entrada"] += amount
            total_entrada += amount
        
        # Build daily data list for all days in range
        daily_data = []
        current_date = start_date.date() if hasattr(start_date, 'date') else start_date
        
        for i in range(days):
            date_obj = current_date + timedelta(days=i)
            date_key = date_obj.strftime("%Y-%m-%d")
            day_key = date_obj.strftime("%d")
            
            entrada = daily_payments.get(date_key, {}).get("entrada", 0.0) if date_key in daily_payments else 0.0
            saida = 0.0  # Expenses are 0 for now (no Expense model)
            
            daily_data.append(DailyCashFlowData(
                day=day_key,
                date=date_key,
                entrada=entrada,
                saida=saida
            ))
        
        # Calculate totals
        total_saida = 0.0  # Expenses are 0 for now
        saldo = total_entrada - total_saida
        
        return DoctorCashFlowResponse(
            total_entrada=total_entrada,
            total_saida=total_saida,
            saldo=saldo,
            daily_data=daily_data
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 403)
        raise
    except Exception as e:
        # Log the error and return a safe response
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_doctor_cash_flow: {str(e)}", exc_info=True)
        
        # Return empty cash flow on error
        return DoctorCashFlowResponse(
            total_entrada=0.0,
            total_saida=0.0,
            saldo=0.0,
            daily_data=[]
        )

