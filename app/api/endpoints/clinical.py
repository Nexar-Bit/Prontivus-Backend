"""
Clinical records, prescriptions, and exam requests API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import joinedload
from fastapi import Body
from fastapi.responses import StreamingResponse
from datetime import datetime, date

from app.core.auth import get_current_user, RoleChecker
from app.models import User, Appointment, Patient, UserRole
from app.models.clinical import ClinicalRecord, Prescription, ExamRequest, Diagnosis, ClinicalRecordVersion
from app.schemas.clinical import (
    ClinicalRecordCreate,
    ClinicalRecordUpdate,
    ClinicalRecordResponse,
    ClinicalRecordDetailResponse,
    DiagnosisBase,
    DiagnosisCreate,
    DiagnosisUpdate,
    DiagnosisResponse,
    PrescriptionBase,
    PrescriptionCreate,
    PrescriptionUpdate,
    PrescriptionResponse,
    ExamRequestBase,
    ExamRequestCreate,
    ExamRequestUpdate,
    ExamRequestResponse,
    PatientClinicalHistoryResponse,
    ClinicalRecordVersionResponse,
)
from database import get_async_session
from io import BytesIO

router = APIRouter(tags=["Clinical"])

# Role checker for doctors (only doctors can create clinical records)
require_doctor = RoleChecker([UserRole.DOCTOR, UserRole.ADMIN])
require_staff = RoleChecker([UserRole.ADMIN, UserRole.SECRETARY, UserRole.DOCTOR])
# ==================== Autosave & Version History ====================

@router.post("/appointments/{appointment_id}/clinical-record/autosave")
async def autosave_clinical_record(
    appointment_id: int,
    record_in: ClinicalRecordUpdate,
    current_user: User = Depends(require_doctor),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Autosave partial SOAP note changes as a version snapshot. Does not modify the current record.
    """
    # Ensure appointment belongs to clinic
    appt = (await db.execute(select(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.clinic_id == current_user.clinic_id
    ))).scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    # Ensure record exists
    rec = (await db.execute(select(ClinicalRecord).filter(ClinicalRecord.appointment_id == appointment_id))).scalar_one_or_none()
    if not rec:
        # create a minimal record to attach autosave
        rec = ClinicalRecord(appointment_id=appointment_id)
        db.add(rec)
        await db.commit()
        await db.refresh(rec)

    version = ClinicalRecordVersion(
        clinical_record_id=rec.id,
        author_user_id=current_user.id,
        is_autosave=True,
        snapshot=record_in.model_dump(exclude_unset=True),
    )
    db.add(version)
    await db.commit()
    return {"success": True, "version_id": version.id}


@router.get("/clinical-records/{record_id}/versions", response_model=List[ClinicalRecordVersionResponse])
async def list_versions(
    record_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_async_session),
):
    versions = (await db.execute(select(ClinicalRecordVersion).filter(ClinicalRecordVersion.clinical_record_id == record_id).order_by(ClinicalRecordVersion.created_at.desc()))).scalars().all()
    return versions



# ==================== Clinical Records ====================

@router.post(
    "/appointments/{appointment_id}/clinical-record",
    response_model=ClinicalRecordDetailResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_or_update_clinical_record(
    appointment_id: int,
    record_in: ClinicalRecordUpdate,
    current_user: User = Depends(require_doctor),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Create or update the SOAP note for a specific appointment
    Only the assigned doctor or admins can create/update clinical records
    """
    # Verify appointment exists and belongs to current clinic
    appointment_query = select(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.clinic_id == current_user.clinic_id
    )
    appointment_result = await db.execute(appointment_query)
    appointment = appointment_result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check if current user is the assigned doctor or admin
    if current_user.role != UserRole.ADMIN and appointment.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned doctor can create clinical records for this appointment"
        )
    
    # Check if clinical record already exists
    existing_record_query = select(ClinicalRecord).filter(
        ClinicalRecord.appointment_id == appointment_id
    )
    existing_record_result = await db.execute(existing_record_query)
    existing_record = existing_record_result.scalar_one_or_none()
    
    if existing_record:
        # Update existing record
        update_data = record_in.model_dump(exclude_unset=True)
        # snapshot before update
        pre_snapshot = {
            "subjective": existing_record.subjective,
            "objective": existing_record.objective,
            "assessment": existing_record.assessment,
            "plan": existing_record.plan,
            "plan_soap": getattr(existing_record, "plan_soap", None),
        }
        for field, value in update_data.items():
            setattr(existing_record, field, value)
        
        await db.commit()
        await db.refresh(existing_record)
        
        # Create version snapshot
        version = ClinicalRecordVersion(
            clinical_record_id=existing_record.id,
            author_user_id=current_user.id,
            is_autosave=False,
            snapshot=pre_snapshot,
        )
        db.add(version)
        await db.commit()
        
        # Reload with relationships
        record_query = select(ClinicalRecord).options(
            joinedload(ClinicalRecord.prescriptions),
            joinedload(ClinicalRecord.exam_requests),
            joinedload(ClinicalRecord.diagnoses)
        ).filter(ClinicalRecord.id == existing_record.id)
        
        record_result = await db.execute(record_query)
        loaded_record = record_result.unique().scalar_one()
        
        return loaded_record
    else:
        # Create new record
        db_record = ClinicalRecord(
            appointment_id=appointment_id,
            **record_in.model_dump(exclude_unset=True)
        )
        db.add(db_record)
        await db.commit()
        await db.refresh(db_record)
        
        # Reload with relationships
        record_query = select(ClinicalRecord).options(
            joinedload(ClinicalRecord.prescriptions),
            joinedload(ClinicalRecord.exam_requests),
            joinedload(ClinicalRecord.diagnoses)
        ).filter(ClinicalRecord.id == db_record.id)
        
        record_result = await db.execute(record_query)
        loaded_record = record_result.unique().scalar_one()
        
        return loaded_record


@router.get(
    "/appointments/{appointment_id}/clinical-record",
    response_model=Optional[ClinicalRecordDetailResponse]
)
async def get_appointment_clinical_record(
    appointment_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get the clinical record for a specific appointment.
    Returns null if no clinical record exists yet.
    """
    # Verify appointment exists and belongs to current clinic
    appointment_query = select(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.clinic_id == current_user.clinic_id
    )
    appointment_result = await db.execute(appointment_query)
    appointment = appointment_result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Get clinical record with relationships
    record_query = select(ClinicalRecord).options(
        joinedload(ClinicalRecord.prescriptions),
        joinedload(ClinicalRecord.exam_requests),
        joinedload(ClinicalRecord.diagnoses)
    ).filter(ClinicalRecord.appointment_id == appointment_id)
    
    record_result = await db.execute(record_query)
    record = record_result.unique().scalar_one_or_none()
    
    # Return null if no record exists (instead of 404)
    return record


@router.get(
    "/patients/{patient_id}/clinical-records",
    response_model=List[PatientClinicalHistoryResponse]
)
async def get_patient_clinical_history(
    patient_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get a patient's complete clinical history
    Returns all appointments with their clinical records, prescriptions, and exam requests
    """
    # Verify patient exists and belongs to current clinic
    patient_query = select(Patient).filter(
        Patient.id == patient_id,
        Patient.clinic_id == current_user.clinic_id
    )
    patient_result = await db.execute(patient_query)
    patient = patient_result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Get all appointments with clinical records
    appointments_query = select(Appointment, User, ClinicalRecord).join(
        User, Appointment.doctor_id == User.id
    ).outerjoin(
        ClinicalRecord, Appointment.id == ClinicalRecord.appointment_id
    ).filter(
        Appointment.patient_id == patient_id,
        Appointment.clinic_id == current_user.clinic_id
    ).order_by(Appointment.scheduled_datetime.desc())
    
    appointments_result = await db.execute(appointments_query)
    appointments_data = appointments_result.all()
    
    history = []
    for appointment, doctor, clinical_record in appointments_data:
        # Load prescriptions and exam requests if clinical record exists
        clinical_record_detail = None
        if clinical_record:
            # Reload with relationships
            record_query = select(ClinicalRecord).options(
                joinedload(ClinicalRecord.prescriptions),
                joinedload(ClinicalRecord.exam_requests),
                joinedload(ClinicalRecord.diagnoses)
            ).filter(ClinicalRecord.id == clinical_record.id)
            record_result = await db.execute(record_query)
            clinical_record_detail = record_result.scalar_one()
        
        history.append(PatientClinicalHistoryResponse(
            appointment_id=appointment.id,
            appointment_date=appointment.scheduled_datetime,
            doctor_name=f"{doctor.first_name} {doctor.last_name}",
            appointment_type=appointment.appointment_type,
            clinical_record=ClinicalRecordDetailResponse.model_validate(clinical_record_detail) if clinical_record_detail else None
        ))
    
    return history


@router.get(
    "/clinical/me/history",
    response_model=List[PatientClinicalHistoryResponse]
)
async def get_my_clinical_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Patient self-access to their clinical history (appointments + clinical records with prescriptions and exam requests).
    Maps the authenticated user to a Patient by email and clinic.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only patients can access their own clinical history")

    # Map user to patient by email
    pat_q = select(Patient).where(Patient.email == current_user.email, Patient.clinic_id == current_user.clinic_id)
    pat_res = await db.execute(pat_q)
    patient = pat_res.scalar_one_or_none()
    if not patient:
        return []

    appts_q = select(Appointment, User, ClinicalRecord).join(
        User, Appointment.doctor_id == User.id
    ).outerjoin(
        ClinicalRecord, Appointment.id == ClinicalRecord.appointment_id
    ).where(
        Appointment.patient_id == patient.id,
        Appointment.clinic_id == current_user.clinic_id
    ).order_by(Appointment.scheduled_datetime.desc())

    appts_res = await db.execute(appts_q)
    appts = appts_res.all()

    out: list[PatientClinicalHistoryResponse] = []
    for appointment, doctor, clinical_record in appts:
        record_detail = None
        if clinical_record:
            rq = select(ClinicalRecord).options(
                joinedload(ClinicalRecord.prescriptions),
                joinedload(ClinicalRecord.exam_requests),
                joinedload(ClinicalRecord.diagnoses)
            ).where(ClinicalRecord.id == clinical_record.id)
            rr = await db.execute(rq)
            record_detail = rr.scalar_one()

        out.append(PatientClinicalHistoryResponse(
            appointment_id=appointment.id,
            appointment_date=appointment.scheduled_datetime,
            doctor_name=f"{doctor.first_name} {doctor.last_name}",
            appointment_type=appointment.appointment_type,
            status=appointment.status,
            clinical_record=ClinicalRecordDetailResponse.model_validate(record_detail) if record_detail else None
        ))
    return out


@router.get(
    "/clinical/doctor/my-clinical-records",
    response_model=List[PatientClinicalHistoryResponse]
)
async def get_my_doctor_clinical_records(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """
    Get all clinical records for the current doctor
    Returns appointments with their clinical records, filtered by doctor_id
    """
    # Only allow doctors to access this endpoint
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for doctors"
        )
    
    # Get all appointments for this doctor with clinical records
    appointments_query = select(Appointment, Patient, User, ClinicalRecord).join(
        Patient, Appointment.patient_id == Patient.id
    ).join(
        User, Appointment.doctor_id == User.id
    ).outerjoin(
        ClinicalRecord, Appointment.id == ClinicalRecord.appointment_id
    ).filter(
        and_(
            Appointment.doctor_id == current_user.id,
            Appointment.clinic_id == current_user.clinic_id
        )
    )
    
    # Apply date filters
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        appointments_query = appointments_query.filter(Appointment.scheduled_datetime >= start_datetime)
    
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        appointments_query = appointments_query.filter(Appointment.scheduled_datetime <= end_datetime)
    
    # Apply search filter
    if search:
        search_filter = or_(
            Patient.first_name.ilike(f"%{search}%"),
            Patient.last_name.ilike(f"%{search}%"),
            Patient.email.ilike(f"%{search}%"),
            Appointment.appointment_type.ilike(f"%{search}%")
        )
        appointments_query = appointments_query.filter(search_filter)
    
    appointments_query = appointments_query.order_by(Appointment.scheduled_datetime.desc())
    appointments_query = appointments_query.offset(skip).limit(limit)
    
    appointments_result = await db.execute(appointments_query)
    appointments_data = appointments_result.all()
    
    records = []
    for appointment, patient, doctor, clinical_record in appointments_data:
        # Load clinical record with relationships if it exists
        clinical_record_detail = None
        if clinical_record:
            record_query = select(ClinicalRecord).options(
                joinedload(ClinicalRecord.prescriptions),
                joinedload(ClinicalRecord.exam_requests),
                joinedload(ClinicalRecord.diagnoses)
            ).filter(ClinicalRecord.id == clinical_record.id)
            record_result = await db.execute(record_query)
            clinical_record_detail = record_result.unique().scalar_one()
        
        # Get patient full name
        patient_name = f"{patient.first_name or ''} {patient.last_name or ''}".strip()
        if not patient_name:
            patient_name = patient.email or "Paciente"
        
        # Get status as string
        appointment_status = appointment.status.value if hasattr(appointment.status, 'value') else str(appointment.status)
        
        records.append(PatientClinicalHistoryResponse(
            appointment_id=appointment.id,
            appointment_date=appointment.scheduled_datetime,
            doctor_name=f"{doctor.first_name} {doctor.last_name}".strip() or doctor.username or "Médico",
            patient_name=patient_name,
            appointment_type=appointment.appointment_type,
            status=appointment_status,
            clinical_record=ClinicalRecordDetailResponse.model_validate(clinical_record_detail) if clinical_record_detail else None
        ))
    
    return records
