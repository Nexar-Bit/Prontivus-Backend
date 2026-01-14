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
from app.models.financial import Invoice, Payment, InvoiceStatus, PaymentStatus, InvoiceLine
from app.models.procedure import Procedure
from database import get_async_session
from pydantic import BaseModel

router = APIRouter(prefix="/doctor", tags=["Doctor Dashboard"])


# ==================== Response Models ====================

class PeriodStats(BaseModel):
    """Statistics for a period (day/week/month)"""
    day: int
    week: int
    month: int

class DoctorDashboardStats(BaseModel):
    """Doctor dashboard statistics with day/week/month breakdown"""
    # Appointments statistics
    appointments: PeriodStats
    # Patients in queue statistics
    queue_patients: PeriodStats
    # Pending records statistics
    pending_records: PeriodStats
    # Revenue statistics (day/week/month)
    revenue_day: float
    revenue_week: float
    revenue_month: float
    
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


class WeeklySummary(BaseModel):
    """Weekly summary statistics"""
    procedures_count: int
    new_consultations_count: int
    returns_count: int

class DoctorDashboardResponse(BaseModel):
    """Doctor dashboard response"""
    stats: DoctorDashboardStats
    upcoming_appointments: List[UpcomingAppointmentResponse]
    weekly_summary: Optional[WeeklySummary] = None
    
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
        
        # Week start (last 7 days for weekly stats)
        week_start = today_start - timedelta(days=6)
        
        # Month start for monthly calculation
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # ==================== Get Appointments Statistics (Day/Week/Month) ====================
        # Today appointments
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
        appointments_day = len(appointments_data)
        
        # Weekly appointments (last 7 days)
        appointments_week_query = select(func.count(Appointment.id)).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.scheduled_datetime >= week_start,
                Appointment.scheduled_datetime < today_end
            )
        )
        appointments_week_result = await db.execute(appointments_week_query)
        appointments_week = appointments_week_result.scalar() or 0
        
        # Monthly appointments
        appointments_month_query = select(func.count(Appointment.id)).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.scheduled_datetime >= month_start,
                Appointment.scheduled_datetime < today_end
            )
        )
        appointments_month_result = await db.execute(appointments_month_query)
        appointments_month = appointments_month_result.scalar() or 0
        
        # ==================== Get Queue Patients Statistics (Day/Week/Month) ====================
        # Day: Current queue (no date filter, it's a current state)
        queue_day_query = select(func.count(Appointment.id)).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.status.in_([
                    AppointmentStatus.CHECKED_IN,
                    AppointmentStatus.IN_CONSULTATION
                ])
            )
        )
        queue_day_result = await db.execute(queue_day_query)
        queue_patients_day = queue_day_result.scalar() or 0
        
        # Week: Count of appointments that were in queue during the week (simplified - using scheduled_datetime)
        queue_week_query = select(func.count(Appointment.id)).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.scheduled_datetime >= week_start,
                Appointment.scheduled_datetime < today_end,
                Appointment.status.in_([
                    AppointmentStatus.CHECKED_IN,
                    AppointmentStatus.IN_CONSULTATION,
                    AppointmentStatus.SCHEDULED
                ])
            )
        )
        queue_week_result = await db.execute(queue_week_query)
        queue_patients_week = queue_week_result.scalar() or 0
        
        # Month: Count of appointments scheduled this month
        queue_month_query = select(func.count(Appointment.id)).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.scheduled_datetime >= month_start,
                Appointment.scheduled_datetime < today_end
            )
        )
        queue_month_result = await db.execute(queue_month_query)
        queue_patients_month = queue_month_result.scalar() or 0
        
        # ==================== Get Pending Clinical Records Statistics (Day/Week/Month) ====================
        # Day: Count appointments completed today without records
        pending_records_day_query = select(func.count(Appointment.id)).outerjoin(
            ClinicalRecord, Appointment.id == ClinicalRecord.appointment_id
        ).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.status == AppointmentStatus.COMPLETED,
                Appointment.completed_at >= today_start,
                Appointment.completed_at < today_end,
                ClinicalRecord.id.is_(None)
            )
        )
        pending_records_day_result = await db.execute(pending_records_day_query)
        pending_records_day = pending_records_day_result.scalar() or 0
        
        # Week: Count appointments completed this week without records
        pending_records_week_query = select(func.count(Appointment.id)).outerjoin(
            ClinicalRecord, Appointment.id == ClinicalRecord.appointment_id
        ).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.status == AppointmentStatus.COMPLETED,
                Appointment.completed_at >= week_start,
                Appointment.completed_at < today_end,
                ClinicalRecord.id.is_(None)
            )
        )
        pending_records_week_result = await db.execute(pending_records_week_query)
        pending_records_week = pending_records_week_result.scalar() or 0
        
        # Month: Count appointments completed this month without records
        pending_records_month_query = select(func.count(Appointment.id)).outerjoin(
            ClinicalRecord, Appointment.id == ClinicalRecord.appointment_id
        ).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.status == AppointmentStatus.COMPLETED,
                Appointment.completed_at >= month_start,
                Appointment.completed_at < today_end,
                ClinicalRecord.id.is_(None)
            )
        )
        pending_records_month_result = await db.execute(pending_records_month_query)
        pending_records_month = pending_records_month_result.scalar() or 0
        
        # ==================== Get Revenue Statistics (Day/Week/Month) ====================
        # Day revenue
        try:
            revenue_day_query = select(func.coalesce(func.sum(Payment.amount), 0)).join(
                Invoice, Payment.invoice_id == Invoice.id
            ).join(
                Appointment, Invoice.appointment_id == Appointment.id
            ).filter(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.clinic_id == current_user.clinic_id,
                    Payment.status == PaymentStatus.COMPLETED,
                    Payment.created_at >= today_start,
                    Payment.created_at < today_end
                )
            )
            revenue_day_result = await db.execute(revenue_day_query)
            revenue_day = float(revenue_day_result.scalar() or 0)
        except Exception:
            revenue_day = 0.0
        
        # Week revenue
        try:
            revenue_week_query = select(func.coalesce(func.sum(Payment.amount), 0)).join(
                Invoice, Payment.invoice_id == Invoice.id
            ).join(
                Appointment, Invoice.appointment_id == Appointment.id
            ).filter(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.clinic_id == current_user.clinic_id,
                    Payment.status == PaymentStatus.COMPLETED,
                    Payment.created_at >= week_start,
                    Payment.created_at < today_end
                )
            )
            revenue_week_result = await db.execute(revenue_week_query)
            revenue_week = float(revenue_week_result.scalar() or 0)
        except Exception:
            revenue_week = 0.0
        
        # Month revenue
        try:
            revenue_month_query = select(func.coalesce(func.sum(Payment.amount), 0)).join(
                Invoice, Payment.invoice_id == Invoice.id
            ).join(
                Appointment, Invoice.appointment_id == Appointment.id
            ).filter(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.clinic_id == current_user.clinic_id,
                    Payment.status == PaymentStatus.COMPLETED,
                    Payment.created_at >= month_start,
                    Payment.created_at < today_end
                )
            )
            revenue_month_result = await db.execute(revenue_month_query)
            revenue_month = float(revenue_month_result.scalar() or 0)
        except Exception:
            revenue_month = 0.0
        
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
        
        # ==================== Get Weekly Summary (Procedures, New Consultations, Returns) ====================
        # Procedures count (from invoices with procedures in the last 7 days)
        procedures_query = select(func.count(func.distinct(InvoiceLine.id))).join(
            Invoice, InvoiceLine.invoice_id == Invoice.id
        ).join(
            Appointment, Invoice.appointment_id == Appointment.id
        ).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                InvoiceLine.procedure_id.isnot(None),
                Invoice.created_at >= week_start,
                Invoice.created_at < today_end
            )
        )
        procedures_result = await db.execute(procedures_query)
        procedures_count = procedures_result.scalar() or 0
        
        # New consultations count (appointments without previous appointments for the same patient)
        # For simplicity, we'll count appointments where appointment_type is not 'follow-up' or 'return'
        new_consultations_query = select(func.count(Appointment.id)).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.scheduled_datetime >= week_start,
                Appointment.scheduled_datetime < today_end,
                or_(
                    Appointment.appointment_type.is_(None),
                    Appointment.appointment_type.notin_(['follow-up', 'return', 'retorno'])
                )
            )
        )
        new_consultations_result = await db.execute(new_consultations_query)
        new_consultations_count = new_consultations_result.scalar() or 0
        
        # Returns count (appointments with appointment_type 'follow-up' or 'return')
        returns_query = select(func.count(Appointment.id)).filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.scheduled_datetime >= week_start,
                Appointment.scheduled_datetime < today_end,
                Appointment.appointment_type.in_(['follow-up', 'return', 'retorno'])
            )
        )
        returns_result = await db.execute(returns_query)
        returns_count = returns_result.scalar() or 0
        
        weekly_summary = WeeklySummary(
            procedures_count=procedures_count,
            new_consultations_count=new_consultations_count,
            returns_count=returns_count
        )
        
        # ==================== Build Response ====================
        stats = DoctorDashboardStats(
            appointments=PeriodStats(
                day=appointments_day,
                week=appointments_week,
                month=appointments_month
            ),
            queue_patients=PeriodStats(
                day=queue_patients_day,
                week=queue_patients_week,
                month=queue_patients_month
            ),
            pending_records=PeriodStats(
                day=pending_records_day,
                week=pending_records_week,
                month=pending_records_month
            ),
            revenue_day=revenue_day,
            revenue_week=revenue_week,
            revenue_month=revenue_month
        )
        
        return DoctorDashboardResponse(
            stats=stats,
            upcoming_appointments=upcoming_appointments[:10],  # Limit to 10 most recent
            weekly_summary=weekly_summary
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
                appointments=PeriodStats(day=0, week=0, month=0),
                queue_patients=PeriodStats(day=0, week=0, month=0),
                pending_records=PeriodStats(day=0, week=0, month=0),
                revenue_day=0.0,
                revenue_week=0.0,
                revenue_month=0.0
            ),
            upcoming_appointments=[],
            weekly_summary=WeeklySummary(
                procedures_count=0,
                new_consultations_count=0,
                returns_count=0
            )
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

