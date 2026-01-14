"""
Appointment management API endpoints
"""
import datetime
import os
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.core.auth import get_current_user, RoleChecker
from app.models import User, Appointment, Patient, UserRole, AppointmentStatus
from app.models.return_approval import ReturnApprovalRequest, ReturnApprovalStatus
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AppointmentListResponse,
    AppointmentStatusUpdate,
)
from pydantic import BaseModel, Field
from app.schemas.return_approval import (
    ReturnApprovalRequestCreate,
    ReturnApprovalRequestUpdate,
    ReturnApprovalRequestResponse,
)
from database import get_async_session
from app.services.realtime import appointment_realtime_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appointments", tags=["Appointments"])

# Role checker for staff (admin, secretary, doctor)
require_staff = RoleChecker([UserRole.ADMIN, UserRole.SECRETARY, UserRole.DOCTOR])


class TodayPatientResponse(BaseModel):
  appointment_id: int
  patient_id: int
  patient_name: str
  doctor_id: int
  doctor_name: str
  scheduled_datetime: datetime.datetime



async def check_slot_availability(
    db: AsyncSession,
    doctor_id: int,
    scheduled_datetime: datetime.datetime,
    clinic_id: int,
    exclude_appointment_id: Optional[int] = None,
    duration_minutes: int = 30,
) -> bool:
    """
    Check if a time slot is available for a doctor
    """
    from datetime import timezone as tz
    
    # Ensure scheduled_datetime is timezone-aware
    if scheduled_datetime.tzinfo is None:
        scheduled_datetime = scheduled_datetime.replace(tzinfo=tz.utc)
    
    start_time = scheduled_datetime
    end_time = scheduled_datetime + datetime.timedelta(minutes=duration_minutes)
    
    # Helper function to make datetime timezone-aware
    def make_aware(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=tz.utc)
        return dt
    
    # Check for overlapping appointments
    query = select(Appointment).filter(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.clinic_id == clinic_id,
            Appointment.status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_CONSULTATION
            ])
        )
    )
    
    if exclude_appointment_id:
        query = query.filter(Appointment.id != exclude_appointment_id)
    
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    # Check for overlap manually to handle timezone-aware comparisons
    for apt in appointments:
        apt_start = make_aware(apt.scheduled_datetime)
        if apt_start:
            apt_end = apt_start + datetime.timedelta(minutes=apt.duration_minutes or 30)
            
            # Check for overlap: appointment starts before this slot ends AND ends after this slot starts
            if not (end_time <= apt_start or start_time >= apt_end):
                return False
    
    return True


@router.get("", response_model=List[AppointmentListResponse])
async def list_appointments(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_async_session),
    start_date: Optional[datetime.date] = Query(None),
    end_date: Optional[datetime.date] = Query(None),
    doctor_id: Optional[int] = Query(None),
    patient_id: Optional[int] = Query(None),
    status: Optional[AppointmentStatus] = Query(None),
):
    """
    List appointments with optional filters
    """
    query = select(Appointment, Patient, User).join(
        Patient, Appointment.patient_id == Patient.id
    ).join(
        User, Appointment.doctor_id == User.id
    ).filter(
        Appointment.clinic_id == current_user.clinic_id
    )
    
    # Apply filters
    if start_date:
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        query = query.filter(Appointment.scheduled_datetime >= start_datetime)
    
    if end_date:
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        query = query.filter(Appointment.scheduled_datetime <= end_datetime)
    
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    
    if patient_id:
        query = query.filter(Appointment.patient_id == patient_id)
    
    if status:
        query = query.filter(Appointment.status == status)
    
    query = query.order_by(Appointment.scheduled_datetime)
    
    result = await db.execute(query)
    appointments_data = result.all()
    
    # Build response with patient and doctor names
    response = []
    for appointment, patient, doctor in appointments_data:
        response.append(AppointmentListResponse(
            id=appointment.id,
            scheduled_datetime=appointment.scheduled_datetime,
            status=appointment.status,
            appointment_type=appointment.appointment_type,
            patient_id=appointment.patient_id,
            doctor_id=appointment.doctor_id,
            patient_name=f"{patient.first_name} {patient.last_name}",
            doctor_name=f"{doctor.first_name} {doctor.last_name}",
        ))
    
    return response


@router.get("/doctor/my-appointments", response_model=List[AppointmentListResponse])
async def get_my_doctor_appointments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    start_date: Optional[datetime.date] = Query(None),
    end_date: Optional[datetime.date] = Query(None),
    status: Optional[AppointmentStatus] = Query(None),
):
    """
    Get appointments for the current doctor - automatically filters by doctor_id
    This endpoint is accessible to doctors only
    """
    # Only allow doctors to access this endpoint
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for doctors"
        )
    
    query = select(Appointment, Patient, User).join(
        Patient, Appointment.patient_id == Patient.id
    ).join(
        User, Appointment.doctor_id == User.id
    ).filter(
        and_(
            Appointment.doctor_id == current_user.id,
            Appointment.clinic_id == current_user.clinic_id
        )
    )
    
    # Apply filters
    if start_date:
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        query = query.filter(Appointment.scheduled_datetime >= start_datetime)
    
    if end_date:
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        query = query.filter(Appointment.scheduled_datetime <= end_datetime)
    
    if status:
        query = query.filter(Appointment.status == status)
    
    query = query.order_by(Appointment.scheduled_datetime)
    
    result = await db.execute(query)
    appointments_data = result.all()
    
    # Build response with patient and doctor names
    response = []
    for appointment, patient, doctor in appointments_data:
        response.append(AppointmentListResponse(
            id=appointment.id,
            scheduled_datetime=appointment.scheduled_datetime,
            status=appointment.status,
            appointment_type=appointment.appointment_type,
            patient_id=appointment.patient_id,
            doctor_id=appointment.doctor_id,
            patient_name=f"{patient.first_name} {patient.last_name}".strip() or patient.email or "Paciente",
            doctor_name=f"{doctor.first_name} {doctor.last_name}".strip() or doctor.username or "Médico",
        ))
    
    return response


@router.get("/patient-appointments", response_model=List[AppointmentListResponse])
async def get_patient_appointments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    status: Optional[AppointmentStatus] = Query(None),
):
    """
    Get appointments for the current user (patient) - NEW ENDPOINT
    This endpoint is accessible to all authenticated users, with role checking inside.
    """
    # Only allow patients to access this endpoint
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for patients"
        )
    
    # Find the patient record that corresponds to the current user
    # Since there's no direct user_id in Patient, we'll match by email
    patient_query = select(Patient).filter(
        and_(
            Patient.email == current_user.email,
            Patient.clinic_id == current_user.clinic_id
        )
    )
    patient_result = await db.execute(patient_query)
    patient = patient_result.scalar_one_or_none()
    
    if not patient:
        # If no patient record found, return empty list
        return []
    
    query = select(Appointment, Patient, User).join(
        Patient, Appointment.patient_id == Patient.id
    ).join(
        User, Appointment.doctor_id == User.id
    ).filter(
        and_(
            Appointment.patient_id == patient.id,
            Appointment.clinic_id == current_user.clinic_id
        )
    )
    
    # Apply status filter if provided
    if status:
        query = query.filter(Appointment.status == status)
    
    result = await db.execute(query)
    appointments = result.all()
    
    appointment_list = []
    for appointment, patient, doctor in appointments:
        appointment_list.append(AppointmentListResponse(
            id=appointment.id,
            patient_id=appointment.patient_id,
            doctor_id=appointment.doctor_id,
            scheduled_datetime=appointment.scheduled_datetime,
            duration_minutes=appointment.duration_minutes,
            status=appointment.status,
            appointment_type=appointment.appointment_type,
            reason=appointment.reason,
            notes=appointment.notes,
            patient_name=patient.full_name,
            doctor_name=doctor.full_name,
            created_at=appointment.created_at,
            updated_at=appointment.updated_at
        ))
    
    return appointment_list


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_patient_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Allow a patient to cancel their own appointment.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only patients can cancel via this endpoint")

    # Map user to patient by email and clinic
    patient_result = await db.execute(select(Patient).filter(and_(Patient.email == current_user.email, Patient.clinic_id == current_user.clinic_id)))
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    appt_result = await db.execute(select(Appointment).filter(and_(Appointment.id == appointment_id, Appointment.patient_id == patient.id, Appointment.clinic_id == current_user.clinic_id)))
    appt = appt_result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appt.status = AppointmentStatus.CANCELLED
    await db.commit()
    await db.refresh(appt)

    # Build response with patient and doctor names
    doc = await db.get(User, appt.doctor_id)
    pat = await db.get(Patient, appt.patient_id)
    return AppointmentResponse(
        id=appt.id,
        patient_id=appt.patient_id,
        doctor_id=appt.doctor_id,
        scheduled_datetime=appt.scheduled_datetime,
        duration_minutes=appt.duration_minutes,
        status=appt.status,
        appointment_type=appt.appointment_type,
        reason=appt.reason,
        notes=appt.notes,
        patient_name=pat.full_name if pat else None,
        doctor_name=f"{doc.first_name} {doc.last_name}" if doc else None,
        created_at=appt.created_at,
        updated_at=appt.updated_at,
    )


class ReschedulePayload(AppointmentUpdate):
    pass


@router.post("/patient/book", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def book_patient_appointment(
    appointment_in: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Allow a patient to book a new appointment
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for patients"
        )
    
    # Map user to patient by email and clinic
    patient_result = await db.execute(
        select(Patient).filter(
            and_(
                Patient.email == current_user.email,
                Patient.clinic_id == current_user.clinic_id
            )
        )
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Ensure appointment is for the current patient
    if appointment_in.patient_id != patient.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create appointment for a different patient"
        )
    
    # Ensure appointment is for the current clinic
    if appointment_in.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create appointment for a different clinic"
        )
    
    # Validate doctor exists and has doctor role
    doctor_query = select(User).filter(
        and_(
            User.id == appointment_in.doctor_id,
            User.clinic_id == current_user.clinic_id,
            User.role == UserRole.DOCTOR
        )
    )
    doctor_result = await db.execute(doctor_query)
    doctor = doctor_result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    
    # Check slot availability
    is_available = await check_slot_availability(
        db,
        appointment_in.doctor_id,
        appointment_in.scheduled_datetime,
        current_user.clinic_id
    )
    
    if not is_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This time slot is not available for the selected doctor"
        )
    
    # Create appointment
    appointment_data = appointment_in.model_dump()
    # Remove payment-related fields that don't belong in Appointment model
    consultation_price = appointment_data.pop("consultation_price", None)
    payment_method = appointment_data.pop("payment_method", None)
    create_invoice_flag = appointment_data.pop("create_invoice", False)
    
    # If no explicit appointment_type was provided, default to doctor's consultation_room (if any)
    if not appointment_data.get("appointment_type") and getattr(doctor, "consultation_room", None):
        appointment_data["appointment_type"] = doctor.consultation_room

    db_appointment = Appointment(**appointment_data)
    db.add(db_appointment)
    await db.commit()
    await db.refresh(db_appointment)
    
    # Optionally create invoice if requested and price is provided
    if create_invoice_flag and (consultation_price or doctor.consultation_fee):
        from decimal import Decimal
        from app.models.financial import Invoice, InvoiceLine, InvoiceStatus, ServiceItem, ServiceCategory
        from datetime import datetime, timedelta, timezone
        
        # Determine the price to use
        price_to_use = Decimal(str(consultation_price)) if consultation_price else (doctor.consultation_fee or Decimal('0'))
        
        if price_to_use:
            # Try to find or create a consultation service item
            service_item_query = select(ServiceItem).filter(
                and_(
                    ServiceItem.clinic_id == current_user.clinic_id,
                    ServiceItem.category == ServiceCategory.CONSULTATION,
                    ServiceItem.is_active == True
                )
            ).limit(1)
            service_item_result = await db.execute(service_item_query)
            service_item = service_item_result.scalar_one_or_none()
            
            # Create invoice
            db_invoice = Invoice(
                clinic_id=current_user.clinic_id,
                patient_id=patient.id,
                appointment_id=db_appointment.id,
                due_date=datetime.now(timezone.utc) + timedelta(days=30),  # Due in 30 days
                status=InvoiceStatus.ISSUED,
                total_amount=price_to_use
            )
            db.add(db_invoice)
            await db.flush()
            
            # Create invoice line
            invoice_line = InvoiceLine(
                invoice_id=db_invoice.id,
                service_item_id=service_item.id if service_item else None,
                quantity=Decimal('1.00'),
                unit_price=price_to_use,
                line_total=price_to_use,
                description=f"Consulta com {doctor.full_name}"
            )
            db.add(invoice_line)
            
            # If payment method is provided, create payment record
            if payment_method:
                from app.models.financial import Payment, PaymentStatus
                payment = Payment(
                    invoice_id=db_invoice.id,
                    amount=price_to_use,
                    method=payment_method,
                    status=PaymentStatus.PENDING,  # Will be marked as completed when actually paid
                    created_by=current_user.id
                )
                db.add(payment)
            
            await db.commit()
    
    # Build response with patient and doctor names
    response = AppointmentResponse.model_validate(db_appointment)
    response.patient_name = patient.full_name
    response.doctor_name = doctor.full_name
    
    # Broadcast event
    await appointment_realtime_manager.broadcast(
        current_user.clinic_id,
        {
            "type": "appointment_created",
            "appointment_id": db_appointment.id,
            "status": str(db_appointment.status),
        },
    )
    
    # Send confirmation email to patient
    if patient.email:
        try:
            from app.services.email_service import email_service
            from datetime import datetime
            
            # Format appointment date and time
            appointment_date = db_appointment.scheduled_datetime.strftime("%d/%m/%Y")
            appointment_time = db_appointment.scheduled_datetime.strftime("%H:%M")
            
            # Get frontend URL
            frontend_url = os.getenv("FRONTEND_URL", "https://prontivus-frontend-p2rr.vercel.app")
            appointment_url = f"{frontend_url}/portal/appointments/{db_appointment.id}"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #0F4C75; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                    .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
                    .appointment-info {{ background-color: white; padding: 20px; margin: 20px 0; border-left: 4px solid #0F4C75; }}
                    .info-item {{ margin: 10px 0; padding: 8px; }}
                    .info-label {{ font-weight: bold; color: #0F4C75; }}
                    .button {{ display: inline-block; padding: 12px 24px; background-color: #0F4C75; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Confirmação de Agendamento</h1>
                    </div>
                    <div class="content">
                        <p>Olá <strong>{patient.first_name}</strong>,</p>
                        <p>Seu agendamento foi confirmado com sucesso!</p>
                        
                        <div class="appointment-info">
                            <div class="info-item">
                                <span class="info-label">Data:</span> {appointment_date}
                            </div>
                            <div class="info-item">
                                <span class="info-label">Horário:</span> {appointment_time}
                            </div>
                            <div class="info-item">
                                <span class="info-label">Médico:</span> {doctor.full_name}
                            </div>
                        </div>
                        
                        <p style="text-align: center;">
                            <a href="{appointment_url}" class="button">Ver Detalhes do Agendamento</a>
                        </p>
                        
                        <p><strong>Lembrete:</strong> Por favor, chegue com 15 minutos de antecedência.</p>
                    </div>
                    <div class="footer">
                        <p>Atenciosamente,<br/><strong>{clinic.name if hasattr(clinic, 'name') else 'Equipe Prontivus'}</strong></p>
                        <p style="margin-top: 20px; font-size: 11px; color: #999;">
                            Este é um e-mail automático. Por favor, não responda a esta mensagem.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = (
                f"Confirmação de Agendamento\n\n"
                f"Olá {patient.first_name},\n\n"
                f"Seu agendamento foi confirmado com sucesso!\n\n"
                f"DADOS DO AGENDAMENTO:\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Data: {appointment_date}\n"
                f"Horário: {appointment_time}\n"
                f"Médico: {doctor.full_name}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Lembrete: Por favor, chegue com 15 minutos de antecedência.\n\n"
                f"Ver detalhes: {appointment_url}\n\n"
                f"Atenciosamente,\n{clinic.name if hasattr(clinic, 'name') else 'Equipe Prontivus'}\n\n"
                f"---\n"
                f"Este é um e-mail automático. Por favor, não responda a esta mensagem."
            )
            
            await email_service.send_email(
                to_email=patient.email,
                subject=f"Confirmação de Agendamento - {appointment_date} às {appointment_time}",
                html_body=html_body,
                text_body=text_body,
            )
        except Exception as e:
            # Don't fail appointment creation if email sending fails
            logger.error(f"Failed to send appointment confirmation email: {str(e)}")
    
    return response


@router.get("/doctor/{doctor_id}/availability")
async def get_doctor_availability(
    doctor_id: int,
    date: datetime.date = Query(..., description="Date to check availability"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get available time slots for a doctor on a specific date
    """
    from datetime import timezone as tz
    
    # Validate doctor exists and belongs to same clinic
    doctor_query = select(User).filter(
        and_(
            User.id == doctor_id,
            User.clinic_id == current_user.clinic_id,
            User.role == UserRole.DOCTOR
        )
    )
    doctor_result = await db.execute(doctor_query)
    doctor = doctor_result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    
    # Get all appointments for this doctor on this date
    # Use timezone-aware datetimes
    start_datetime = datetime.datetime.combine(date, datetime.time.min).replace(tzinfo=tz.utc)
    end_datetime = datetime.datetime.combine(date, datetime.time.max).replace(tzinfo=tz.utc)
    
    appointments_query = select(Appointment).filter(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.clinic_id == current_user.clinic_id,
            Appointment.scheduled_datetime >= start_datetime,
            Appointment.scheduled_datetime <= end_datetime,
            Appointment.status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_CONSULTATION
            ])
        )
    )
    appointments_result = await db.execute(appointments_query)
    appointments = appointments_result.scalars().all()
    
    # Helper function to make datetime timezone-aware
    def make_aware(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=tz.utc)
        return dt
    
    # Generate time slots (8:00 to 18:00, 30-minute intervals)
    available_slots = []
    start_hour = 8
    end_hour = 18
    
    for hour in range(start_hour, end_hour):
        for minute in [0, 30]:
            slot_time = datetime.datetime.combine(date, datetime.time(hour, minute)).replace(tzinfo=tz.utc)
            slot_end = slot_time + datetime.timedelta(minutes=30)
            
            # Check if this slot conflicts with any appointment
            is_available = True
            for apt in appointments:
                apt_start = make_aware(apt.scheduled_datetime)
                if apt_start:
                    apt_end = apt_start + datetime.timedelta(minutes=apt.duration_minutes or 30)
                    
                    # Check for overlap
                    if not (slot_end <= apt_start or slot_time >= apt_end):
                        is_available = False
                        break
            
            available_slots.append({
                "time": slot_time.strftime("%H:%M"),
                "datetime": slot_time.isoformat(),
                "available": is_available
            })
    
    return {
        "doctor_id": doctor_id,
        "doctor_name": f"{doctor.first_name} {doctor.last_name}",
        "date": date.isoformat(),
        "slots": available_slots
    }


@router.get("/today-patients", response_model=list[TodayPatientResponse])
async def get_today_patients(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Return patients with appointments today for the current clinic.

    - Doctors see only their own appointments.
    - Secretaries/Admins see all doctors' appointments.
    """
    from datetime import timezone as tz

    now = datetime.datetime.now(tz.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + datetime.timedelta(days=1)

    query = select(Appointment, Patient, User).join(
        Patient, Appointment.patient_id == Patient.id
    ).join(
        User, Appointment.doctor_id == User.id
    ).filter(
        and_(
            Appointment.clinic_id == current_user.clinic_id,
            Appointment.scheduled_datetime >= today_start,
            Appointment.scheduled_datetime < today_end,
        )
    )

    # If doctor, restrict to their own appointments
    if current_user.role == UserRole.DOCTOR:
        query = query.filter(Appointment.doctor_id == current_user.id)

    result = await db.execute(query.order_by(Appointment.scheduled_datetime))
    rows = result.all()

    # Deduplicate by (appointment_id) – we want one entry per appointment
    out: list[TodayPatientResponse] = []
    for appt, patient, doctor in rows:
        patient_name = f"{patient.first_name or ''} {patient.last_name or ''}".strip() or patient.email or "Paciente"
        doctor_name = f"{doctor.first_name or ''} {doctor.last_name or ''}".strip() or doctor.username or "Médico"
        out.append(
            TodayPatientResponse(
                appointment_id=appt.id,
                patient_id=patient.id,
                patient_name=patient_name,
                doctor_id=doctor.id,
                doctor_name=doctor_name,
                scheduled_datetime=appt.scheduled_datetime,
            )
        )

    return out


# ==================== Return Approval Requests ====================

@router.post("/return-approval-requests", response_model=ReturnApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_return_approval_request(
    request_data: ReturnApprovalRequestCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Create a return approval request (secretary requests approval for multiple returns)
    """
    # Only secretaries and admins can create approval requests
    if current_user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only secretaries and admins can create approval requests"
        )
    
    # Verify patient exists
    patient_query = select(Patient).filter(
        and_(
            Patient.id == request_data.patient_id,
            Patient.clinic_id == current_user.clinic_id
        )
    )
    patient_result = await db.execute(patient_query)
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Verify doctor exists
    doctor_query = select(User).filter(
        and_(
            User.id == request_data.doctor_id,
            User.clinic_id == current_user.clinic_id,
            User.role == UserRole.DOCTOR
        )
    )
    doctor_result = await db.execute(doctor_query)
    doctor = doctor_result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    
    # Set expiration date (7 days from now)
    from datetime import timezone, timedelta
    expires_at = datetime.datetime.now(timezone.utc) + timedelta(days=7)
    
    # Create approval request
    approval_request = ReturnApprovalRequest(
        patient_id=request_data.patient_id,
        doctor_id=request_data.doctor_id,
        clinic_id=current_user.clinic_id,
        requested_appointment_date=request_data.requested_appointment_date,
        appointment_type=request_data.appointment_type,
        notes=request_data.notes,
        returns_count_this_month=request_data.returns_count_this_month,
        status=ReturnApprovalStatus.PENDING,
        requested_by=current_user.id,
        expires_at=expires_at
    )
    
    db.add(approval_request)
    await db.commit()
    await db.refresh(approval_request)
    
    # Load relationships for response
    await db.refresh(approval_request, ["patient", "doctor", "requester", "approver"])
    
    # Build response manually to ensure proper enum conversion
    response = ReturnApprovalRequestResponse(
        id=approval_request.id,
        patient_id=approval_request.patient_id,
        doctor_id=approval_request.doctor_id,
        clinic_id=approval_request.clinic_id,
        requested_appointment_date=approval_request.requested_appointment_date,
        appointment_type=approval_request.appointment_type,
        notes=approval_request.notes,
        returns_count_this_month=approval_request.returns_count_this_month,
        status=approval_request.status.value if approval_request.status else "pending",
        requested_by=approval_request.requested_by,
        approved_by=approval_request.approved_by,
        approval_notes=approval_request.approval_notes,
        resulting_appointment_id=approval_request.resulting_appointment_id,
        requested_at=approval_request.requested_at,
        reviewed_at=approval_request.reviewed_at,
        expires_at=approval_request.expires_at,
        created_at=getattr(approval_request, 'created_at', approval_request.requested_at),
        updated_at=getattr(approval_request, 'updated_at', None),
        patient_name=f"{patient.first_name} {patient.last_name}",
        doctor_name=f"{doctor.first_name} {doctor.last_name}",
        requester_name=f"{current_user.first_name} {current_user.last_name}",
        approver_name=None,
    )
    
    return response


@router.get("/return-approval-requests", response_model=List[ReturnApprovalRequestResponse])
async def get_return_approval_requests(
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected, expired"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get return approval requests
    - Doctors see requests for their appointments
    - Secretaries/Admins see all requests
    """
    try:
        query = select(ReturnApprovalRequest).filter(
            ReturnApprovalRequest.clinic_id == current_user.clinic_id
        )
        
        # Doctors only see their own requests
        if current_user.role == UserRole.DOCTOR:
            query = query.filter(ReturnApprovalRequest.doctor_id == current_user.id)
        
        # Filter by status (convert to lowercase to match enum)
        if status_filter:
            try:
                status_lower = status_filter.lower().strip()
                # Map lowercase string to enum value (not enum name)
                # SQLAlchemy needs the enum value string, not the enum constant
                status_map = {
                    'pending': ReturnApprovalStatus.PENDING.value,  # Use .value to get "pending"
                    'approved': ReturnApprovalStatus.APPROVED.value,  # Use .value to get "approved"
                    'rejected': ReturnApprovalStatus.REJECTED.value,  # Use .value to get "rejected"
                    'expired': ReturnApprovalStatus.EXPIRED.value,  # Use .value to get "expired"
                }
                if status_lower in status_map:
                    # Cast the column to string and compare with the enum value
                    from sqlalchemy import cast, String
                    query = query.filter(
                        cast(ReturnApprovalRequest.status, String) == status_map[status_lower]
                    )
                else:
                    logger.warning(f"Invalid status filter: {status_filter}, ignoring")
            except Exception as e:
                # Invalid status filter, ignore it
                logger.warning(f"Error processing status filter {status_filter}: {str(e)}, ignoring")
                pass
        
        query = query.order_by(ReturnApprovalRequest.requested_at.desc())
        
        # Load relationships using joinedload for better performance
        from sqlalchemy.orm import joinedload
        query = query.options(
            joinedload(ReturnApprovalRequest.patient),
            joinedload(ReturnApprovalRequest.doctor),
            joinedload(ReturnApprovalRequest.requester),
            joinedload(ReturnApprovalRequest.approver)
        )
        
        result = await db.execute(query)
        requests = result.unique().scalars().all()
        
        responses = []
        for req in requests:
            try:
                # Get created_at and updated_at safely
                created_at = getattr(req, 'created_at', None) or req.requested_at
                updated_at = getattr(req, 'updated_at', None)
                
                # Get status value safely
                status_value = req.status.value if hasattr(req.status, 'value') else str(req.status) if req.status else "pending"
                
                # Manually construct response to ensure proper enum conversion
                response = ReturnApprovalRequestResponse(
                    id=req.id,
                    patient_id=req.patient_id,
                    doctor_id=req.doctor_id,
                    clinic_id=req.clinic_id,
                    requested_appointment_date=req.requested_appointment_date,
                    appointment_type=req.appointment_type or "retorno",
                    notes=req.notes,
                    returns_count_this_month=req.returns_count_this_month or 0,
                    status=status_value,
                    requested_by=req.requested_by,
                    approved_by=req.approved_by,
                    approval_notes=req.approval_notes,
                    resulting_appointment_id=req.resulting_appointment_id,
                    requested_at=req.requested_at,
                    reviewed_at=req.reviewed_at,
                    expires_at=req.expires_at,
                    created_at=created_at,
                    updated_at=updated_at,
                    patient_name=f"{req.patient.first_name} {req.patient.last_name}" if req.patient and req.patient.first_name else None,
                    doctor_name=f"{req.doctor.first_name} {req.doctor.last_name}" if req.doctor and req.doctor.first_name else None,
                    requester_name=f"{req.requester.first_name} {req.requester.last_name}" if req.requester and req.requester.first_name else None,
                    approver_name=f"{req.approver.first_name} {req.approver.last_name}" if req.approver and req.approver.first_name else None,
                )
                responses.append(response)
            except Exception as e:
                logger.error(f"Error processing return approval request {req.id}: {str(e)}")
                # Skip this request if there's an error processing it
                continue
        
        return responses
    except Exception as e:
        logger.error(f"Error getting return approval requests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading return approval requests: {str(e)}"
        )


@router.patch("/return-approval-requests/{request_id}", response_model=ReturnApprovalRequestResponse)
async def update_return_approval_request(
    request_id: int,
    update_data: ReturnApprovalRequestUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Approve or reject a return approval request (doctors only)
    """
    # Only doctors can approve/reject
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can approve or reject return approval requests"
        )
    
    # Get the request
    request_query = select(ReturnApprovalRequest).filter(
        and_(
            ReturnApprovalRequest.id == request_id,
            ReturnApprovalRequest.clinic_id == current_user.clinic_id,
            ReturnApprovalRequest.doctor_id == current_user.id
        )
    )
    request_result = await db.execute(request_query)
    approval_request = request_result.scalar_one_or_none()
    
    if not approval_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found"
        )
    
    if approval_request.status != ReturnApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request is already {approval_request.status.value}"
        )
    
    # Check if expired
    from datetime import timezone
    if approval_request.expires_at and approval_request.expires_at < datetime.datetime.now(timezone.utc):
        approval_request.status = ReturnApprovalStatus.EXPIRED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval request has expired"
        )
    
    # Update status (convert to lowercase to match enum)
    status_lower = update_data.status.lower() if update_data.status else None
    if not status_lower:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status is required"
        )
    new_status = ReturnApprovalStatus(status_lower)
    approval_request.status = new_status
    approval_request.approved_by = current_user.id
    approval_request.approval_notes = update_data.approval_notes
    approval_request.reviewed_at = datetime.datetime.now(timezone.utc)
    
    # If approved, create the appointment
    if new_status == ReturnApprovalStatus.APPROVED:
        appointment = Appointment(
            patient_id=approval_request.patient_id,
            doctor_id=approval_request.doctor_id,
            clinic_id=approval_request.clinic_id,
            scheduled_datetime=approval_request.requested_appointment_date,
            appointment_type=approval_request.appointment_type,
            notes=approval_request.notes,
            status=AppointmentStatus.SCHEDULED
        )
        db.add(appointment)
        await db.flush()
        approval_request.resulting_appointment_id = appointment.id
    
    # Update updated_at timestamp
    approval_request.updated_at = datetime.datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(approval_request)
    
    # Load relationships
    await db.refresh(approval_request, ["patient", "doctor", "requester", "approver"])
    
    # Build response manually to ensure proper enum conversion
    response = ReturnApprovalRequestResponse(
        id=approval_request.id,
        patient_id=approval_request.patient_id,
        doctor_id=approval_request.doctor_id,
        clinic_id=approval_request.clinic_id,
        requested_appointment_date=approval_request.requested_appointment_date,
        appointment_type=approval_request.appointment_type,
        notes=approval_request.notes,
        returns_count_this_month=approval_request.returns_count_this_month,
        status=approval_request.status.value if approval_request.status else "pending",
        requested_by=approval_request.requested_by,
        approved_by=approval_request.approved_by,
        approval_notes=approval_request.approval_notes,
        resulting_appointment_id=approval_request.resulting_appointment_id,
        requested_at=approval_request.requested_at,
        reviewed_at=approval_request.reviewed_at,
        expires_at=approval_request.expires_at,
        created_at=getattr(approval_request, 'created_at', approval_request.requested_at),
        updated_at=getattr(approval_request, 'updated_at', None),
        patient_name=f"{approval_request.patient.first_name} {approval_request.patient.last_name}" if approval_request.patient else None,
        doctor_name=f"{approval_request.doctor.first_name} {approval_request.doctor.last_name}" if approval_request.doctor else None,
        requester_name=f"{approval_request.requester.first_name} {approval_request.requester.last_name}" if approval_request.requester else None,
        approver_name=f"{approval_request.approver.first_name} {approval_request.approver.last_name}" if approval_request.approver else None,
    )
    
    return response


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_patient_appointment(
    appointment_id: int,
    payload: ReschedulePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Allow a patient to reschedule their own appointment (date/time and optional reason/notes).
    Checks slot availability for the same doctor.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only patients can reschedule via this endpoint")

    patient_result = await db.execute(select(Patient).filter(and_(Patient.email == current_user.email, Patient.clinic_id == current_user.clinic_id)))
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    appt_result = await db.execute(select(Appointment).filter(and_(Appointment.id == appointment_id, Appointment.patient_id == patient.id, Appointment.clinic_id == current_user.clinic_id)))
    appt = appt_result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Only reschedule datetime (and optional reason/notes)
    if payload.scheduled_datetime:
        available = await check_slot_availability(db, appt.doctor_id, payload.scheduled_datetime, current_user.clinic_id, exclude_appointment_id=appt.id, duration_minutes=payload.duration_minutes or appt.duration_minutes)
        if not available:
            raise HTTPException(status_code=400, detail="Selected time slot is not available")
        appt.scheduled_datetime = payload.scheduled_datetime
    if payload.duration_minutes:
        appt.duration_minutes = payload.duration_minutes
    if payload.reason is not None:
        appt.reason = payload.reason
    if payload.notes is not None:
        appt.notes = payload.notes

    await db.commit()
    await db.refresh(appt)

    doc = await db.get(User, appt.doctor_id)
    pat = await db.get(Patient, appt.patient_id)
    return AppointmentResponse(
        id=appt.id,
        patient_id=appt.patient_id,
        doctor_id=appt.doctor_id,
        scheduled_datetime=appt.scheduled_datetime,
        duration_minutes=appt.duration_minutes,
        status=appt.status,
        appointment_type=appt.appointment_type,
        reason=appt.reason,
        notes=appt.notes,
        patient_name=pat.full_name if pat else None,
        doctor_name=f"{doc.first_name} {doc.last_name}" if doc else None,
        created_at=appt.created_at,
        updated_at=appt.updated_at,
    )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get a specific appointment by ID
    """
    query = select(Appointment, Patient, User).join(
        Patient, Appointment.patient_id == Patient.id
    ).join(
        User, Appointment.doctor_id == User.id
    ).filter(
        and_(
            Appointment.id == appointment_id,
            Appointment.clinic_id == current_user.clinic_id
        )
    )
    
    result = await db.execute(query)
    appointment_data = result.first()
    
    if not appointment_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    appointment, patient, doctor = appointment_data
    
    # Create response with additional fields
    response = AppointmentResponse.model_validate(appointment)
    response.patient_name = f"{patient.first_name} {patient.last_name}"
    response.doctor_name = f"{doctor.first_name} {doctor.last_name}"
    
    return response


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_in: AppointmentCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Create a new appointment
    """
    # Ensure the appointment is created for the current user's clinic
    if appointment_in.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create appointment for a different clinic"
        )
    
    # Validate patient exists
    patient_query = select(Patient).filter(
        and_(
            Patient.id == appointment_in.patient_id,
            Patient.clinic_id == current_user.clinic_id
        )
    )
    patient_result = await db.execute(patient_query)
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Validate doctor exists and has doctor role
    doctor_query = select(User).filter(
        and_(
            User.id == appointment_in.doctor_id,
            User.clinic_id == current_user.clinic_id,
            User.role == UserRole.DOCTOR
        )
    )
    doctor_result = await db.execute(doctor_query)
    doctor = doctor_result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    
    # Check slot availability
    is_available = await check_slot_availability(
        db,
        appointment_in.doctor_id,
        appointment_in.scheduled_datetime,
        current_user.clinic_id
    )
    
    if not is_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This time slot is not available for the selected doctor"
        )
    
    # Check return appointment limit (30% of daily appointments)
    appointment_datetime = appointment_in.scheduled_datetime
    if isinstance(appointment_datetime, str):
        appointment_datetime = datetime.datetime.fromisoformat(appointment_datetime.replace('Z', '+00:00'))
    
    # Check if this is a return appointment
    is_return = appointment_in.appointment_type and appointment_in.appointment_type.lower() in ['follow-up', 'return', 'retorno']
    
    if is_return:
        # Get the date (without time)
        if hasattr(appointment_datetime, 'date'):
            appointment_date = appointment_datetime.date()
        else:
            appointment_date = appointment_datetime
        
        # Get start and end of the day in UTC
        from datetime import timezone
        day_start = datetime.datetime.combine(appointment_date, datetime.time.min).replace(tzinfo=timezone.utc)
        day_end = datetime.datetime.combine(appointment_date, datetime.time.max).replace(tzinfo=timezone.utc)
        
        # Count total appointments for the day
        total_appointments_query = select(func.count(Appointment.id)).filter(
            and_(
                Appointment.doctor_id == appointment_in.doctor_id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.scheduled_datetime >= day_start,
                Appointment.scheduled_datetime <= day_end,
                Appointment.status != AppointmentStatus.CANCELLED
            )
        )
        total_appointments_result = await db.execute(total_appointments_query)
        total_appointments = total_appointments_result.scalar() or 0
        
        # Count return appointments for the day
        returns_query = select(func.count(Appointment.id)).filter(
            and_(
                Appointment.doctor_id == appointment_in.doctor_id,
                Appointment.clinic_id == current_user.clinic_id,
                Appointment.scheduled_datetime >= day_start,
                Appointment.scheduled_datetime <= day_end,
                Appointment.appointment_type.in_(['follow-up', 'return', 'retorno']),
                Appointment.status != AppointmentStatus.CANCELLED
            )
        )
        returns_result = await db.execute(returns_query)
        returns_count = returns_result.scalar() or 0
        
        # Calculate 30% limit (minimum 1 slot if there are any appointments)
        max_returns = max(1, int(total_appointments * 0.3)) if total_appointments > 0 else 0
        
        # Check if limit is exceeded
        if returns_count >= max_returns:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Limite de retornos atingido para este dia. Máximo permitido: {max_returns} (30% dos {total_appointments} agendamentos do dia). Já agendados: {returns_count}."
            )
    
    # Create appointment
    appointment_data = appointment_in.model_dump()
    # Remove payment-related fields that don't belong in Appointment model
    consultation_price = appointment_data.pop("consultation_price", None)
    payment_method = appointment_data.pop("payment_method", None)
    create_invoice_flag = appointment_data.pop("create_invoice", False)
    
    # If no explicit appointment_type was provided, default to doctor's consultation_room (if any)
    if not appointment_data.get("appointment_type") and getattr(doctor, "consultation_room", None):
        appointment_data["appointment_type"] = doctor.consultation_room

    db_appointment = Appointment(**appointment_data)
    db.add(db_appointment)
    await db.commit()
    await db.refresh(db_appointment)
    
    # Optionally create invoice if requested and price is provided
    if create_invoice_flag and consultation_price:
        from decimal import Decimal
        from app.models.financial import Invoice, InvoiceLine, InvoiceStatus, ServiceItem, ServiceCategory
        from datetime import datetime, timedelta, timezone
        
        # Determine the price to use
        price_to_use = Decimal(str(consultation_price))
        if not price_to_use and doctor.consultation_fee:
            price_to_use = doctor.consultation_fee
        
        if price_to_use:
            # Try to find or create a consultation service item
            service_item_query = select(ServiceItem).filter(
                and_(
                    ServiceItem.clinic_id == current_user.clinic_id,
                    ServiceItem.category == ServiceCategory.CONSULTATION,
                    ServiceItem.is_active == True
                )
            ).limit(1)
            service_item_result = await db.execute(service_item_query)
            service_item = service_item_result.scalar_one_or_none()
            
            # Create invoice
            db_invoice = Invoice(
                clinic_id=current_user.clinic_id,
                patient_id=patient.id,
                appointment_id=db_appointment.id,
                due_date=datetime.now(timezone.utc) + timedelta(days=30),  # Due in 30 days
                status=InvoiceStatus.ISSUED,
                total_amount=price_to_use
            )
            db.add(db_invoice)
            await db.flush()
            
            # Create invoice line
            invoice_line = InvoiceLine(
                invoice_id=db_invoice.id,
                service_item_id=service_item.id if service_item else None,
                quantity=Decimal('1.00'),
                unit_price=price_to_use,
                line_total=price_to_use,
                description=f"Consulta com {doctor.full_name}"
            )
            db.add(invoice_line)
            
            # If payment method is provided, create payment record
            if payment_method:
                from app.models.financial import Payment, PaymentStatus
                payment = Payment(
                    invoice_id=db_invoice.id,
                    amount=price_to_use,
                    method=payment_method,
                    status=PaymentStatus.PENDING,  # Will be marked as completed when actually paid
                    created_by=current_user.id
                )
                db.add(payment)
            
            await db.commit()
    
    # Add patient and doctor names to response
    response = AppointmentResponse.model_validate(db_appointment)
    response.patient_name = patient.full_name
    response.doctor_name = doctor.full_name
    
    # Broadcast event
    await appointment_realtime_manager.broadcast(
        current_user.clinic_id,
        {
            "type": "appointment_created",
            "appointment_id": db_appointment.id,
            "status": str(db_appointment.status),
        },
    )
    
    # Send confirmation email to patient
    if patient.email:
        try:
            from app.services.email_service import email_service
            from app.models import Clinic
            
            # Get clinic info
            clinic_query = select(Clinic).filter(Clinic.id == current_user.clinic_id)
            clinic_result = await db.execute(clinic_query)
            clinic = clinic_result.scalar_one_or_none()
            
            # Format appointment date and time
            appointment_date = db_appointment.scheduled_datetime.strftime("%d/%m/%Y")
            appointment_time = db_appointment.scheduled_datetime.strftime("%H:%M")
            
            # Get frontend URL
            frontend_url = os.getenv("FRONTEND_URL", "https://prontivus-frontend-p2rr.vercel.app")
            appointment_url = f"{frontend_url}/portal/appointments/{db_appointment.id}"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #0F4C75; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                    .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
                    .appointment-info {{ background-color: white; padding: 20px; margin: 20px 0; border-left: 4px solid #0F4C75; }}
                    .info-item {{ margin: 10px 0; padding: 8px; }}
                    .info-label {{ font-weight: bold; color: #0F4C75; }}
                    .button {{ display: inline-block; padding: 12px 24px; background-color: #0F4C75; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Confirmação de Agendamento</h1>
                    </div>
                    <div class="content">
                        <p>Olá <strong>{patient.first_name}</strong>,</p>
                        <p>Seu agendamento foi confirmado com sucesso!</p>
                        
                        <div class="appointment-info">
                            <div class="info-item">
                                <span class="info-label">Data:</span> {appointment_date}
                            </div>
                            <div class="info-item">
                                <span class="info-label">Horário:</span> {appointment_time}
                            </div>
                            <div class="info-item">
                                <span class="info-label">Médico:</span> {doctor.full_name}
                            </div>
                        </div>
                        
                        <p style="text-align: center;">
                            <a href="{appointment_url}" class="button">Ver Detalhes do Agendamento</a>
                        </p>
                        
                        <p><strong>Lembrete:</strong> Por favor, chegue com 15 minutos de antecedência.</p>
                    </div>
                    <div class="footer">
                        <p>Atenciosamente,<br/><strong>{clinic.name if clinic else 'Equipe Prontivus'}</strong></p>
                        <p style="margin-top: 20px; font-size: 11px; color: #999;">
                            Este é um e-mail automático. Por favor, não responda a esta mensagem.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = (
                f"Confirmação de Agendamento\n\n"
                f"Olá {patient.first_name},\n\n"
                f"Seu agendamento foi confirmado com sucesso!\n\n"
                f"DADOS DO AGENDAMENTO:\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Data: {appointment_date}\n"
                f"Horário: {appointment_time}\n"
                f"Médico: {doctor.full_name}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Lembrete: Por favor, chegue com 15 minutos de antecedência.\n\n"
                f"Ver detalhes: {appointment_url}\n\n"
                f"Atenciosamente,\n{clinic.name if clinic else 'Equipe Prontivus'}\n\n"
                f"---\n"
                f"Este é um e-mail automático. Por favor, não responda a esta mensagem."
            )
            
            await email_service.send_email(
                to_email=patient.email,
                subject=f"Confirmação de Agendamento - {appointment_date} às {appointment_time}",
                html_body=html_body,
                text_body=text_body,
            )
        except Exception as e:
            # Don't fail appointment creation if email sending fails
            logger.error(f"Failed to send appointment confirmation email: {str(e)}")

    return response


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    appointment_in: AppointmentUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update an appointment
    """
    # Get existing appointment
    query = select(Appointment).filter(
        and_(
            Appointment.id == appointment_id,
            Appointment.clinic_id == current_user.clinic_id
        )
    )
    result = await db.execute(query)
    db_appointment = result.scalar_one_or_none()
    
    if not db_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # If rescheduling, check slot availability
    if appointment_in.scheduled_datetime:
        doctor_id = appointment_in.doctor_id or db_appointment.doctor_id
        is_available = await check_slot_availability(
            db,
            doctor_id,
            appointment_in.scheduled_datetime,
            current_user.clinic_id,
            exclude_appointment_id=appointment_id
        )
        
        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This time slot is not available for the selected doctor"
            )
    
    # Update appointment fields
    update_data = appointment_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_appointment, field, value)
    
    await db.commit()
    await db.refresh(db_appointment)
    
    # Get patient and doctor names
    patient_query = select(Patient).filter(Patient.id == db_appointment.patient_id)
    patient_result = await db.execute(patient_query)
    patient = patient_result.scalar_one()
    
    doctor_query = select(User).filter(User.id == db_appointment.doctor_id)
    doctor_result = await db.execute(doctor_query)
    doctor = doctor_result.scalar_one()
    
    response = AppointmentResponse.model_validate(db_appointment)
    response.patient_name = patient.full_name
    response.doctor_name = doctor.full_name
    
    # Broadcast event
    await appointment_realtime_manager.broadcast(
        current_user.clinic_id,
        {
            "type": "appointment_updated",
            "appointment_id": db_appointment.id,
            "status": str(db_appointment.status),
        },
    )

    return response


@router.get("/doctor/queue", response_model=List[dict])
async def get_doctor_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get the queue of patients for the current doctor
    Returns patients with status CHECKED_IN (waiting) and IN_CONSULTATION (in consultation)
    """
    from datetime import timezone as tz
    
    # Only allow doctors to access this endpoint
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for doctors"
        )
    
    now = datetime.datetime.now(tz.utc)
    
    # Get all appointments for today with status CHECKED_IN or IN_CONSULTATION
    queue_query = select(Appointment, Patient).join(
        Patient, Appointment.patient_id == Patient.id
    ).filter(
        and_(
            Appointment.doctor_id == current_user.id,
            Appointment.clinic_id == current_user.clinic_id,
            Appointment.status.in_([
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_CONSULTATION
            ]),
            # Only today's appointments
            Appointment.scheduled_datetime >= now.replace(hour=0, minute=0, second=0, microsecond=0),
            Appointment.scheduled_datetime < (now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1))
        )
    ).order_by(
        # IN_CONSULTATION first, then by scheduled_datetime
        Appointment.status.desc(),
        Appointment.scheduled_datetime
    )
    
    result = await db.execute(queue_query)
    appointments_data = result.all()
    
    queue_items = []
    for appointment, patient in appointments_data:
        # Calculate wait time
        wait_time_minutes = 0
        wait_time_str = "0 min"
        
        if appointment.status == AppointmentStatus.CHECKED_IN:
            # Calculate from checked_in_at or scheduled_datetime
            if appointment.checked_in_at:
                wait_start = appointment.checked_in_at
            else:
                wait_start = appointment.scheduled_datetime
            
            if wait_start:
                # Make timezone-aware if needed
                if wait_start.tzinfo is None:
                    wait_start = wait_start.replace(tzinfo=tz.utc)
                
                wait_delta = now - wait_start
                wait_time_minutes = int(wait_delta.total_seconds() / 60)
                wait_time_str = f"{wait_time_minutes} min"
        elif appointment.status == AppointmentStatus.IN_CONSULTATION:
            # Calculate from started_at
            if appointment.started_at:
                wait_start = appointment.started_at
                if wait_start.tzinfo is None:
                    wait_start = wait_start.replace(tzinfo=tz.utc)
                
                wait_delta = now - wait_start
                wait_time_minutes = int(wait_delta.total_seconds() / 60)
                wait_time_str = f"{wait_time_minutes} min"
        
        # Get patient name
        patient_name = f"{patient.first_name or ''} {patient.last_name or ''}".strip()
        if not patient_name:
            patient_name = patient.email or "Paciente"
        
        # Format appointment time
        apt_datetime = appointment.scheduled_datetime
        if apt_datetime.tzinfo is None:
            apt_datetime = apt_datetime.replace(tzinfo=tz.utc)
        appointment_time = apt_datetime.strftime("%H:%M")
        
        queue_items.append({
            "id": appointment.id,
            "patient_id": patient.id,
            "patient_name": patient_name,
            "appointment_time": appointment_time,
            "scheduled_datetime": appointment.scheduled_datetime.isoformat(),
            "wait_time": wait_time_str,
            "wait_time_minutes": wait_time_minutes,
            "status": appointment.status.value if hasattr(appointment.status, 'value') else str(appointment.status),
            "appointment_type": appointment.appointment_type,
            "checked_in_at": appointment.checked_in_at.isoformat() if appointment.checked_in_at else None,
            "started_at": appointment.started_at.isoformat() if appointment.started_at else None,
        })
    
    return queue_items


@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
async def update_appointment_status(
    appointment_id: int,
    status_update: AppointmentStatusUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update appointment status (check-in, start consultation, complete, cancel)
    """
    from datetime import timezone as tz
    
    query = select(Appointment).filter(
        and_(
            Appointment.id == appointment_id,
            Appointment.clinic_id == current_user.clinic_id
        )
    )
    result = await db.execute(query)
    db_appointment = result.scalar_one_or_none()
    
    if not db_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Update status and timestamps
    old_status = db_appointment.status
    db_appointment.status = status_update.status
    now = datetime.datetime.now(tz.utc)
    
    # Update timestamps based on status
    if status_update.status == AppointmentStatus.CHECKED_IN:
        if not db_appointment.checked_in_at:
            db_appointment.checked_in_at = now
    elif status_update.status == AppointmentStatus.IN_CONSULTATION:
        if not db_appointment.started_at:
            db_appointment.started_at = now
    elif status_update.status == AppointmentStatus.COMPLETED:
        if not db_appointment.completed_at:
            db_appointment.completed_at = now
    
    await db.commit()
    await db.refresh(db_appointment)
    
    # Get patient and doctor names
    patient_query = select(Patient).filter(Patient.id == db_appointment.patient_id)
    patient_result = await db.execute(patient_query)
    patient = patient_result.scalar_one()
    
    doctor_query = select(User).filter(User.id == db_appointment.doctor_id)
    doctor_result = await db.execute(doctor_query)
    doctor = doctor_result.scalar_one()
    
    response = AppointmentResponse.model_validate(db_appointment)
    response.patient_name = patient.full_name
    response.doctor_name = doctor.full_name
    
    # Send completion email with documents if appointment was completed
    if status_update.status == AppointmentStatus.COMPLETED and patient.email:
        try:
            from app.services.email_service import email_service
            from app.models import Clinic
            from app.models.clinical import ClinicalRecord
            from app.api.endpoints.documents import _get_consultation_data
            from app.services.pdf_generator import PDFGenerator
            
            # Get clinic info
            clinic_query = select(Clinic).filter(Clinic.id == current_user.clinic_id)
            clinic_result = await db.execute(clinic_query)
            clinic = clinic_result.scalar_one_or_none()
            
            # Format appointment date
            appointment_date = db_appointment.scheduled_datetime.strftime("%d/%m/%Y")
            appointment_time = db_appointment.scheduled_datetime.strftime("%H:%M")
            
            # Get frontend URL
            frontend_url = os.getenv("FRONTEND_URL", "https://prontivus-frontend-p2rr.vercel.app")
            appointment_url = f"{frontend_url}/portal/appointments/{db_appointment.id}"
            
            # Prepare attachments
            attachments = []
            
            # Generate consultation PDF if clinical record exists
            try:
                # Check if clinical record exists
                clinical_record_query = select(ClinicalRecord).filter(
                    ClinicalRecord.appointment_id == appointment_id
                )
                clinical_record_result = await db.execute(clinical_record_query)
                clinical_record = clinical_record_result.scalar_one_or_none()
                
                if clinical_record:
                    # Get consultation data
                    consultation_data = await _get_consultation_data(appointment_id, current_user, db)
                    
                    # Generate PDF
                    pdf_generator = PDFGenerator()
                    pdf_bytes = pdf_generator.generate_consultation_report(consultation_data)
                    
                    # Add PDF as attachment
                    filename = f"consulta_{appointment_id}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
                    attachments.append((filename, pdf_bytes, "application/pdf"))
            except Exception as pdf_error:
                logger.warning(f"Failed to generate consultation PDF for email: {str(pdf_error)}")
                # Continue without PDF attachment
            
            # Create email content
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #10b981; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                    .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
                    .info-box {{ background-color: white; padding: 20px; margin: 20px 0; border-left: 4px solid #10b981; }}
                    .info-item {{ margin: 10px 0; padding: 8px; }}
                    .info-label {{ font-weight: bold; color: #10b981; }}
                    .button {{ display: inline-block; padding: 12px 24px; background-color: #10b981; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                    .attachment-note {{ background-color: #e0f2fe; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Atendimento Concluído</h1>
                    </div>
                    <div class="content">
                        <p>Olá <strong>{patient.first_name}</strong>,</p>
                        <p>Seu atendimento foi concluído com sucesso!</p>
                        
                        <div class="info-box">
                            <div class="info-item">
                                <span class="info-label">Data:</span> {appointment_date}
                            </div>
                            <div class="info-item">
                                <span class="info-label">Horário:</span> {appointment_time}
                            </div>
                            <div class="info-item">
                                <span class="info-label">Médico:</span> {doctor.full_name}
                            </div>
                        </div>
                        
                        {f'<div class="attachment-note"><strong>📎 Documentos:</strong> Os documentos da consulta foram anexados a este e-mail.</div>' if attachments else ''}
                        
                        <p style="text-align: center;">
                            <a href="{appointment_url}" class="button">Ver Detalhes do Atendimento</a>
                        </p>
                        
                        <p>Obrigado por escolher <strong>{clinic.name if clinic else 'nossa clínica'}</strong>!</p>
                    </div>
                    <div class="footer">
                        <p>Atenciosamente,<br/><strong>{clinic.name if clinic else 'Equipe Prontivus'}</strong></p>
                        <p style="margin-top: 20px; font-size: 11px; color: #999;">
                            Este é um e-mail automático. Por favor, não responda a esta mensagem.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = (
                f"Atendimento Concluído\n\n"
                f"Olá {patient.first_name},\n\n"
                f"Seu atendimento foi concluído com sucesso!\n\n"
                f"DADOS DO ATENDIMENTO:\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Data: {appointment_date}\n"
                f"Horário: {appointment_time}\n"
                f"Médico: {doctor.full_name}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{'📎 Os documentos da consulta foram anexados a este e-mail.\n\n' if attachments else ''}"
                f"Ver detalhes: {appointment_url}\n\n"
                f"Obrigado por escolher {clinic.name if clinic else 'nossa clínica'}!\n\n"
                f"Atenciosamente,\n{clinic.name if clinic else 'Equipe Prontivus'}\n\n"
                f"---\n"
                f"Este é um e-mail automático. Por favor, não responda a esta mensagem."
            )
            
            await email_service.send_email(
                to_email=patient.email,
                subject=f"Atendimento Concluído - {appointment_date}",
                html_body=html_body,
                text_body=text_body,
                attachments=attachments if attachments else None,
            )
        except Exception as e:
            # Don't fail status update if email sending fails
            logger.error(f"Failed to send completion email: {str(e)}")
    
    # Broadcast status change
    await appointment_realtime_manager.broadcast(
        current_user.clinic_id,
        {
            "type": "appointment_status",
            "appointment_id": db_appointment.id,
            "status": str(db_appointment.status),
        },
    )

    return response


@router.websocket("/ws/appointments")
async def appointments_ws(websocket: WebSocket):
    """WebSocket channel for appointment updates, tenant-isolated via header token parsing upstream middleware.
    Requires AuthenticationMiddleware to set request.state.user_id and ideally clinic_id in token.
    We parse Authorization header from websocket headers manually and fetch clinic_id from token using existing logic.
    """
    try:
        # Extract Authorization header or token query param
        auth_header = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
        clinic_id: int | None = None
        token_value: str | None = None
        if auth_header and auth_header.startswith("Bearer "):
            token_value = auth_header.split(" ")[1]
        if not token_value:
            try:
                # Parse query string from URL
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(str(websocket.url))
                query_params = parse_qs(parsed_url.query)
                token_value = query_params.get("token", [None])[0]
            except Exception:
                token_value = None
        if token_value:
            try:
                from app.core.auth import verify_token
                payload = verify_token(token_value)
                clinic_id = payload.get("clinic_id")
            except Exception as e:
                print(f"Token verification failed: {e}")
                clinic_id = None
        if clinic_id is None:
            # Reject if tenant unknown
            await websocket.close(code=4401, reason="Invalid or missing token")
            return

        await appointment_realtime_manager.connect(clinic_id, websocket)
        try:
            while True:
                # Keep the socket alive; we don't expect inbound messages right now
                await websocket.receive_text()
        except WebSocketDisconnect:
            await appointment_realtime_manager.disconnect(clinic_id, websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close(code=4400, reason="Internal error")
        except:
            pass


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Delete an appointment (admin only)
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete appointments"
        )
    
    query = select(Appointment).filter(
        and_(
            Appointment.id == appointment_id,
            Appointment.clinic_id == current_user.clinic_id
        )
    )
    result = await db.execute(query)
    db_appointment = result.scalar_one_or_none()
    
    if not db_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    await db.delete(db_appointment)
    await db.commit()
    
    return None


@router.post("/{appointment_id}/consultation-token")
async def generate_consultation_token(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Generate a unique room token for video consultation
    """
    # Verify appointment exists and user has access
    appointment_query = select(Appointment).filter(
        and_(
            Appointment.id == appointment_id,
            or_(
                Appointment.patient_id == current_user.id,  # Patient can access their own appointments
                Appointment.doctor_id == current_user.id,   # Doctor can access their appointments
                current_user.role == UserRole.ADMIN,        # Admin can access all
                current_user.role == UserRole.SECRETARY     # Secretary can access all
            )
        )
    )
    appointment_result = await db.execute(appointment_query)
    appointment = appointment_result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or access denied"
        )
    
    # Check if appointment is scheduled for today or in the future
    now = datetime.datetime.now(datetime.timezone.utc)
    if appointment.scheduled_datetime < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate token for past appointments"
        )
    
    # Generate a unique room token
    import secrets
    room_token = f"room_{appointment_id}_{secrets.token_urlsafe(16)}"
    
    return {
        "token": room_token,
        "appointment_id": appointment_id,
        "expires_at": appointment.scheduled_datetime.isoformat(),
        "room_name": f"consultation-{appointment_id}"
    }


@router.get("/available-slots")
async def get_available_slots(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    doctor_id: int = Query(..., description="Doctor ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get available time slots for a specific doctor on a specific date
    """
    try:
        # Parse date
        appointment_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    # Verify doctor exists
    doctor_query = select(User).filter(
        and_(
            User.id == doctor_id,
            User.role == UserRole.DOCTOR,
            User.clinic_id == current_user.clinic_id
        )
    )
    doctor_result = await db.execute(doctor_query)
    doctor = doctor_result.scalar_one_or_none()
    
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    
    # Generate time slots (9 AM to 5 PM, 30-minute intervals)
    time_slots = []
    start_time = datetime.time(9, 0)  # 9:00 AM
    end_time = datetime.time(17, 0)   # 5:00 PM
    
    current_time = start_time
    while current_time < end_time:
        slot_datetime = datetime.datetime.combine(appointment_date, current_time)
        slot_datetime = slot_datetime.replace(tzinfo=datetime.timezone.utc)
        
        # Check if slot is available
        is_available = await check_slot_availability(
            db, doctor_id, slot_datetime, 30
        )
        
        time_slots.append({
            "time": current_time.strftime("%H:%M"),
            "available": is_available,
            "datetime": slot_datetime.isoformat()
        })
        
        # Move to next slot (30 minutes)
        current_time = datetime.time(
            current_time.hour,
            current_time.minute + 30
        )
    
    return time_slots


# ==================== Patient History for Appointment Creation ====================

class PatientAppointmentHistoryResponse(BaseModel):
    """Patient appointment history for appointment creation suggestions"""
    last_appointment_date: Optional[datetime.datetime] = None
    last_appointment_type: Optional[str] = None
    returns_count_this_month: int = 0
    returns_count_total: int = 0
    last_consultation_date: Optional[datetime.datetime] = None
    suggested_date: Optional[datetime.date] = None
    message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


@router.get("/patient/{patient_id}/history", response_model=PatientAppointmentHistoryResponse)
async def get_patient_appointment_history(
    patient_id: int,
    doctor_id: Optional[int] = Query(None, description="Filter by doctor ID (optional)"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get patient appointment history for appointment creation suggestions
    
    Returns:
    - Last appointment date and type
    - Count of returns this month and total
    - Last consultation date
    - Suggested date based on return count
    - Message with notification for secretary
    """
    # Verify patient exists and belongs to current clinic
    patient_query = select(Patient).filter(
        and_(
            Patient.id == patient_id,
            Patient.clinic_id == current_user.clinic_id
        )
    )
    patient_result = await db.execute(patient_query)
    patient = patient_result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Get all appointments for this patient
    appointments_query = select(Appointment).filter(
        and_(
            Appointment.patient_id == patient_id,
            Appointment.clinic_id == current_user.clinic_id,
            Appointment.status != AppointmentStatus.CANCELLED
        )
    )
    
    # Filter by doctor if provided
    if doctor_id:
        appointments_query = appointments_query.filter(Appointment.doctor_id == doctor_id)
    
    appointments_query = appointments_query.order_by(Appointment.scheduled_datetime.desc())
    
    appointments_result = await db.execute(appointments_query)
    appointments = appointments_result.scalars().all()
    
    if not appointments:
        return PatientAppointmentHistoryResponse(
            last_appointment_date=None,
            last_appointment_type=None,
            returns_count_this_month=0,
            returns_count_total=0,
            last_consultation_date=None,
            suggested_date=None,
            message="Paciente sem histórico de consultas anteriores."
        )
    
    # Get current month start and end
    now = datetime.datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get last appointment
    last_appointment = appointments[0]
    last_appointment_date = last_appointment.scheduled_datetime
    last_appointment_type = last_appointment.appointment_type
    
    # Count returns this month
    returns_this_month = [
        apt for apt in appointments
        if apt.scheduled_datetime >= month_start
        and apt.appointment_type
        and apt.appointment_type.lower() in ['follow-up', 'return', 'retorno']
    ]
    returns_count_this_month = len(returns_this_month)
    
    # Count total returns
    returns_total = [
        apt for apt in appointments
        if apt.appointment_type
        and apt.appointment_type.lower() in ['follow-up', 'return', 'retorno']
    ]
    returns_count_total = len(returns_total)
    
    # Get last consultation (non-return)
    last_consultation = None
    for apt in appointments:
        if apt.appointment_type and apt.appointment_type.lower() not in ['follow-up', 'return', 'retorno']:
            last_consultation = apt
            break
    
    last_consultation_date = last_consultation.scheduled_datetime if last_consultation else None
    
    # Calculate suggested date
    suggested_date = None
    message = None
    
    if last_appointment_date:
        # If more than one return, suggest next month
        if returns_count_this_month > 1:
            # Suggest next month
            if now.month == 12:
                suggested_date = datetime.date(now.year + 1, 1, 1)
            else:
                suggested_date = datetime.date(now.year, now.month + 1, 1)
            message = f"⚠️ Atenção: Paciente já possui {returns_count_this_month} retornos agendados este mês. Recomendado agendar para o próximo mês."
        else:
            # Suggest based on last appointment date (30 days later)
            last_date = last_appointment_date.date() if hasattr(last_appointment_date, 'date') else last_appointment_date
            suggested_date = last_date + datetime.timedelta(days=30)
            if suggested_date < now.date():
                suggested_date = now.date() + datetime.timedelta(days=7)  # At least 7 days from now
            message = f"📅 Última consulta: {last_date.strftime('%d/%m/%Y')}. Sugestão de data: {suggested_date.strftime('%d/%m/%Y')}"
    
    return PatientAppointmentHistoryResponse(
        last_appointment_date=last_appointment_date,
        last_appointment_type=last_appointment_type,
        returns_count_this_month=returns_count_this_month,
        returns_count_total=returns_count_total,
        last_consultation_date=last_consultation_date,
        suggested_date=suggested_date,
        message=message
    )


# ==================== Doctor Procedures ====================

@router.get("/doctor/{doctor_id}/procedures")
async def get_doctor_procedures(
    doctor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get procedures available for a specific doctor
    Returns ServiceItems from the clinic that are procedures
    """
    # Verify doctor exists and belongs to current clinic
    doctor_query = select(User).filter(
        and_(
            User.id == doctor_id,
            User.clinic_id == current_user.clinic_id,
            User.role == UserRole.DOCTOR
        )
    )
    doctor_result = await db.execute(doctor_query)
    doctor = doctor_result.scalar_one_or_none()
    
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    
    # Get ServiceItems that are procedures for this clinic
    from app.models.financial import ServiceItem, ServiceCategory
    procedures_query = select(ServiceItem).filter(
        and_(
            ServiceItem.clinic_id == current_user.clinic_id,
            ServiceItem.is_active == True,
            ServiceItem.category == ServiceCategory.PROCEDURE
        )
    ).order_by(ServiceItem.name)
    
    procedures_result = await db.execute(procedures_query)
    procedures = procedures_result.scalars().all()
    
    # Also get general Procedure model items
    from app.models.procedure import Procedure
    procedure_query = select(Procedure).filter(
        and_(
            Procedure.clinic_id == current_user.clinic_id,
            Procedure.is_active == True
        )
    ).order_by(Procedure.name)
    
    procedure_result = await db.execute(procedure_query)
    procedure_items = procedure_result.scalars().all()
    
    # Combine both into a unified response
    result = []
    
    # Add ServiceItems
    for item in procedures:
        result.append({
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "code": item.code,
            "price": float(item.price),
            "category": item.category.value,
            "type": "service_item"
        })
    
    # Add Procedures
    for proc in procedure_items:
        result.append({
            "id": proc.id,
            "name": proc.name,
            "description": proc.description,
            "code": None,
            "price": float(proc.cost),
            "category": "procedure",
            "type": "procedure"
        })
    
    return result

