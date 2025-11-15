"""
Secretary Dashboard API Endpoints
Provides aggregated data for secretary dashboard
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import joinedload

from app.core.auth import get_current_user, RoleChecker
from app.models import User, Patient, Appointment, AppointmentStatus, UserRole
from app.models.financial import ServiceItem, PaymentMethod, Payment, Invoice
from app.models import Product
from database import get_async_session
from pydantic import BaseModel

router = APIRouter(prefix="/secretary", tags=["Secretary Dashboard"])

# Role checker for secretary
require_secretary = RoleChecker([UserRole.SECRETARY, UserRole.ADMIN])


# ==================== Response Models ====================

class SecretaryDashboardStats(BaseModel):
    """Secretary dashboard statistics"""
    today_appointments_count: int
    confirmed_appointments_count: int
    total_patients_count: int
    pending_tasks_count: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TodayAppointmentResponse(BaseModel):
    """Today's appointment response"""
    id: int
    patient_name: str
    doctor_name: str
    scheduled_datetime: datetime
    status: str
    appointment_type: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SecretaryDashboardResponse(BaseModel):
    """Complete secretary dashboard response"""
    stats: SecretaryDashboardStats
    today_appointments: List[TodayAppointmentResponse]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class RegistrationStatsResponse(BaseModel):
    """Registration statistics response"""
    total_patients: int
    total_supplies: int
    total_doctors: int
    total_products: int
    total_payment_methods: int
    total_registrations: int
    active_registrations: int
    today_updates: int


# ==================== Dashboard Endpoint ====================

@router.get("/dashboard", response_model=SecretaryDashboardResponse)
async def get_secretary_dashboard(
    current_user: User = Depends(require_secretary),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get comprehensive secretary dashboard data
    
    Returns:
    - Statistics (counts of appointments, patients, etc.)
    - Today's appointments list
    """
    try:
        # Use timezone-aware datetime to avoid comparison errors
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # ==================== Get Today's Appointments ====================
        today_appointments_query = select(Appointment, Patient, User).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            User, Appointment.doctor_id == User.id
        ).filter(
            and_(
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.scheduled_datetime >= today_start,
                Appointment.scheduled_datetime < today_end
            )
        ).order_by(Appointment.scheduled_datetime)
        
        appointments_result = await db.execute(today_appointments_query)
        appointments_data = appointments_result.all()
        
        # Helper function to make datetime timezone-aware if needed
        def make_aware(dt):
            if dt is None:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        
        # Build today's appointments list
        today_appointments = []
        confirmed_count = 0
        for appointment, patient, doctor in appointments_data:
            # Get patient name safely
            patient_name = f"{patient.first_name or ''} {patient.last_name or ''}".strip()
            if not patient_name:
                patient_name = patient.email or "Paciente"
            
            # Get doctor name safely
            doctor_name = f"{doctor.first_name or ''} {doctor.last_name or ''}".strip()
            if not doctor_name:
                doctor_name = doctor.username or "Médico"
            
            # Count confirmed appointments (scheduled status)
            appointment_status = appointment.status
            if isinstance(appointment_status, AppointmentStatus):
                if appointment_status == AppointmentStatus.SCHEDULED:
                    confirmed_count += 1
                status_value = appointment_status.value
            else:
                status_value = str(appointment_status)
                if status_value.lower() in ['scheduled', 'agendado', 'confirmado']:
                    confirmed_count += 1
            
            apt_datetime = make_aware(appointment.scheduled_datetime)
            
            today_appointments.append(TodayAppointmentResponse(
                id=appointment.id,
                patient_name=patient_name,
                doctor_name=doctor_name,
                scheduled_datetime=apt_datetime or now,
                status=status_value,
                appointment_type=appointment.appointment_type
            ))
        
        # ==================== Get Total Patients ====================
        patients_query = select(func.count(Patient.id)).filter(
            and_(
                Patient.clinic_id == current_user.clinic_id,
                Patient.is_active == True
            )
        )
        patients_result = await db.execute(patients_query)
        total_patients = patients_result.scalar() or 0
        
        # ==================== Build Response ====================
        stats = SecretaryDashboardStats(
            today_appointments_count=len(today_appointments),
            confirmed_appointments_count=confirmed_count,
            total_patients_count=total_patients,
            pending_tasks_count=0  # TODO: Implement task system if needed
        )
        
        return SecretaryDashboardResponse(
            stats=stats,
            today_appointments=today_appointments
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_secretary_dashboard: {str(e)}", exc_info=True)
        
        # Return empty dashboard on error to prevent frontend crashes
        return SecretaryDashboardResponse(
            stats=SecretaryDashboardStats(
                today_appointments_count=0,
                confirmed_appointments_count=0,
                total_patients_count=0,
                pending_tasks_count=0
            ),
            today_appointments=[]
        )


@router.get("/registration-stats", response_model=RegistrationStatsResponse)
async def get_registration_stats(
    current_user: User = Depends(require_secretary),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get registration statistics for the cadastros page
    
    Returns:
    - Counts for patients, supplies (products), doctors, service items, payment methods
    - Total and active registrations
    - Today's updates count
    """
    try:
        # Use timezone-aware datetime to avoid comparison errors
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # ==================== Get Total Patients ====================
        patients_query = select(func.count(Patient.id)).filter(
            and_(
                Patient.clinic_id == current_user.clinic_id,
                Patient.is_active == True
            )
        )
        patients_result = await db.execute(patients_query)
        total_patients = patients_result.scalar() or 0
        
        # ==================== Get Total Supplies (Products) ====================
        supplies_query = select(func.count(Product.id)).filter(
            and_(
                Product.clinic_id == current_user.clinic_id,
                Product.is_active == True
            )
        )
        supplies_result = await db.execute(supplies_query)
        total_supplies = supplies_result.scalar() or 0
        
        # ==================== Get Total Doctors ====================
        doctors_query = select(func.count(User.id)).filter(
            and_(
                User.clinic_id == current_user.clinic_id,
                User.role == UserRole.DOCTOR,
                User.is_active == True
            )
        )
        doctors_result = await db.execute(doctors_query)
        total_doctors = doctors_result.scalar() or 0
        
        # ==================== Get Total Products (Service Items) ====================
        products_query = select(func.count(ServiceItem.id)).filter(
            and_(
                ServiceItem.clinic_id == current_user.clinic_id,
                ServiceItem.is_active == True
            )
        )
        products_result = await db.execute(products_query)
        total_products = products_result.scalar() or 0
        
        # ==================== Get Total Payment Methods ====================
        # PaymentMethod is an enum, so we count distinct payment methods used in payments
        # Payment doesn't have clinic_id directly, so we join with Invoice
        payment_methods_query = select(func.count(func.distinct(Payment.method))).join(
            Invoice, Payment.invoice_id == Invoice.id
        ).filter(
            Invoice.clinic_id == current_user.clinic_id
        )
        payment_methods_result = await db.execute(payment_methods_query)
        total_payment_methods = payment_methods_result.scalar() or 0
        
        # If no payments exist, return a default count (common payment methods)
        if total_payment_methods == 0:
            total_payment_methods = 5  # Default: cash, credit, debit, pix, insurance
        
        # ==================== Calculate Totals ====================
        total_registrations = total_patients + total_supplies + total_doctors + total_products + total_payment_methods
        active_registrations = total_patients + total_supplies + total_doctors + total_products + total_payment_methods
        
        # ==================== Get Today's Updates ====================
        # Count records updated today (patients, products, service items, users)
        today_patients_query = select(func.count(Patient.id)).filter(
            and_(
                Patient.clinic_id == current_user.clinic_id,
                Patient.updated_at >= today_start
            )
        )
        today_patients_result = await db.execute(today_patients_query)
        today_patients = today_patients_result.scalar() or 0
        
        today_products_query = select(func.count(Product.id)).filter(
            and_(
                Product.clinic_id == current_user.clinic_id,
                Product.updated_at >= today_start
            )
        )
        today_products_result = await db.execute(today_products_query)
        today_products = today_products_result.scalar() or 0
        
        today_service_items_query = select(func.count(ServiceItem.id)).filter(
            and_(
                ServiceItem.clinic_id == current_user.clinic_id,
                ServiceItem.updated_at >= today_start
            )
        )
        today_service_items_result = await db.execute(today_service_items_query)
        today_service_items = today_service_items_result.scalar() or 0
        
        today_users_query = select(func.count(User.id)).filter(
            and_(
                User.clinic_id == current_user.clinic_id,
                User.role == UserRole.DOCTOR,
                User.updated_at >= today_start
            )
        )
        today_users_result = await db.execute(today_users_query)
        today_users = today_users_result.scalar() or 0
        
        today_updates = today_patients + today_products + today_service_items + today_users
        
        return RegistrationStatsResponse(
            total_patients=total_patients,
            total_supplies=total_supplies,
            total_doctors=total_doctors,
            total_products=total_products,
            total_payment_methods=total_payment_methods,
            total_registrations=total_registrations,
            active_registrations=active_registrations,
            today_updates=today_updates
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_registration_stats: {str(e)}", exc_info=True)
        
        # Return default values on error
        return RegistrationStatsResponse(
            total_patients=0,
            total_supplies=0,
            total_doctors=0,
            total_products=0,
            total_payment_methods=0,
            total_registrations=0,
            active_registrations=0,
            today_updates=0
        )
