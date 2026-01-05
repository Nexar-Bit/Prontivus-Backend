"""
Patient Telemetry API Endpoints
Handles patient health metrics and vital signs tracking
"""

from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func as sql_func, desc
from sqlalchemy.orm import selectinload
from decimal import Decimal

from database import get_async_session
from app.core.auth import get_current_user
from app.models import User, UserRole, Patient
from app.models.telemetry import PatientTelemetry
from app.schemas.telemetry import (
    TelemetryCreate,
    TelemetryResponse,
    TelemetryUpdate,
    TelemetryStatsResponse
)

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.post("", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED)
async def create_telemetry_record(
    telemetry_data: TelemetryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a new telemetry record for the current patient
    Patients can only create records for themselves
    Staff can create records for any patient in their clinic
    """
    try:
        # Determine patient_id
        if current_user.role == UserRole.PATIENT:
            # Get patient record
            patient_query = select(Patient).filter(
                and_(
                    Patient.email == current_user.email,
                    Patient.clinic_id == current_user.clinic_id
                )
            )
            patient_result = await db.execute(patient_query)
            patient = patient_result.scalar_one_or_none()
            
            if not patient:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Patient record not found"
                )
            
            patient_id = patient.id
        else:
            # Staff creating for a specific patient
            patient_id = telemetry_data.patient_id
            if not patient_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="patient_id is required for staff users"
                )
            
            # Verify patient exists and belongs to clinic
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
        
        # Calculate BMI if weight and height provided
        bmi = None
        if telemetry_data.weight and telemetry_data.height:
            # BMI = weight (kg) / (height (m))^2
            height_m = telemetry_data.height / 100.0
            bmi = float(telemetry_data.weight / (height_m * height_m))
        
        # Create telemetry record
        record_data = telemetry_data.model_dump(exclude={'patient_id', 'bmi'})
        record_data['patient_id'] = patient_id
        record_data['clinic_id'] = current_user.clinic_id
        if bmi:
            record_data['bmi'] = Decimal(str(bmi))
        if current_user.role != UserRole.PATIENT:
            record_data['recorded_by'] = current_user.id
        
        telemetry_record = PatientTelemetry(**record_data)
        db.add(telemetry_record)
        await db.flush()
        await db.commit()
        await db.refresh(telemetry_record)
        
        return TelemetryResponse(
            id=telemetry_record.id,
            patient_id=telemetry_record.patient_id,
            clinic_id=telemetry_record.clinic_id,
            measured_at=telemetry_record.measured_at,
            systolic_bp=float(telemetry_record.systolic_bp) if telemetry_record.systolic_bp else None,
            diastolic_bp=float(telemetry_record.diastolic_bp) if telemetry_record.diastolic_bp else None,
            heart_rate=float(telemetry_record.heart_rate) if telemetry_record.heart_rate else None,
            temperature=float(telemetry_record.temperature) if telemetry_record.temperature else None,
            oxygen_saturation=float(telemetry_record.oxygen_saturation) if telemetry_record.oxygen_saturation else None,
            respiratory_rate=float(telemetry_record.respiratory_rate) if telemetry_record.respiratory_rate else None,
            weight=float(telemetry_record.weight) if telemetry_record.weight else None,
            height=float(telemetry_record.height) if telemetry_record.height else None,
            bmi=float(telemetry_record.bmi) if telemetry_record.bmi else None,
            steps=telemetry_record.steps,
            calories_burned=float(telemetry_record.calories_burned) if telemetry_record.calories_burned else None,
            activity_minutes=telemetry_record.activity_minutes,
            sleep_hours=float(telemetry_record.sleep_hours) if telemetry_record.sleep_hours else None,
            sleep_quality=telemetry_record.sleep_quality,
            blood_glucose=float(telemetry_record.blood_glucose) if telemetry_record.blood_glucose else None,
            additional_metrics=telemetry_record.additional_metrics,
            notes=telemetry_record.notes,
            source=telemetry_record.source,
            device_id=telemetry_record.device_id,
            is_verified=telemetry_record.is_verified,
            recorded_by=telemetry_record.recorded_by,
            created_at=telemetry_record.created_at,
            updated_at=telemetry_record.updated_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating telemetry record: {str(e)}"
        )


@router.get("/me", response_model=List[TelemetryResponse])
async def get_my_telemetry(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get telemetry records for the current patient"""
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for patients"
        )
    try:
        # Get patient record
        patient_query = select(Patient).filter(
            and_(
                Patient.email == current_user.email,
                Patient.clinic_id == current_user.clinic_id
            )
        )
        patient_result = await db.execute(patient_query)
        patient = patient_result.scalar_one_or_none()
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient record not found"
            )
        
        # Build query
        query = select(PatientTelemetry).filter(
            PatientTelemetry.patient_id == patient.id
        )
        
        # Apply date filters
        if start_date:
            query = query.filter(PatientTelemetry.measured_at >= start_date)
        if end_date:
            query = query.filter(PatientTelemetry.measured_at <= end_date)
        
        # Order by measured_at descending
        query = query.order_by(desc(PatientTelemetry.measured_at))
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        return [
            TelemetryResponse(
                id=r.id,
                patient_id=r.patient_id,
                clinic_id=r.clinic_id,
                measured_at=r.measured_at,
                systolic_bp=float(r.systolic_bp) if r.systolic_bp else None,
                diastolic_bp=float(r.diastolic_bp) if r.diastolic_bp else None,
                heart_rate=float(r.heart_rate) if r.heart_rate else None,
                temperature=float(r.temperature) if r.temperature else None,
                oxygen_saturation=float(r.oxygen_saturation) if r.oxygen_saturation else None,
                respiratory_rate=float(r.respiratory_rate) if r.respiratory_rate else None,
                weight=float(r.weight) if r.weight else None,
                height=float(r.height) if r.height else None,
                bmi=float(r.bmi) if r.bmi else None,
                steps=r.steps,
                calories_burned=float(r.calories_burned) if r.calories_burned else None,
                activity_minutes=r.activity_minutes,
                sleep_hours=float(r.sleep_hours) if r.sleep_hours else None,
                sleep_quality=r.sleep_quality,
                blood_glucose=float(r.blood_glucose) if r.blood_glucose else None,
                additional_metrics=r.additional_metrics,
                notes=r.notes,
                source=r.source,
                device_id=r.device_id,
                is_verified=r.is_verified,
                recorded_by=r.recorded_by,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in records
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching telemetry records: {str(e)}"
        )


@router.get("/patients/{patient_id}", response_model=List[TelemetryResponse])
async def get_patient_telemetry(
    patient_id: int,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get telemetry records for a specific patient (staff only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.DOCTOR, UserRole.SECRETARY]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for staff"
        )
    # Verify patient belongs to clinic
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
    
    # Build query
    query = select(PatientTelemetry).filter(
        PatientTelemetry.patient_id == patient_id,
        PatientTelemetry.clinic_id == current_user.clinic_id
    )
    
    # Apply date filters
    if start_date:
        query = query.filter(PatientTelemetry.measured_at >= start_date)
    if end_date:
        query = query.filter(PatientTelemetry.measured_at <= end_date)
    
    # Order by measured_at descending
    query = query.order_by(desc(PatientTelemetry.measured_at))
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    return [
        TelemetryResponse(
            id=r.id,
            patient_id=r.patient_id,
            clinic_id=r.clinic_id,
            measured_at=r.measured_at,
            systolic_bp=float(r.systolic_bp) if r.systolic_bp else None,
            diastolic_bp=float(r.diastolic_bp) if r.diastolic_bp else None,
            heart_rate=float(r.heart_rate) if r.heart_rate else None,
            temperature=float(r.temperature) if r.temperature else None,
            oxygen_saturation=float(r.oxygen_saturation) if r.oxygen_saturation else None,
            respiratory_rate=float(r.respiratory_rate) if r.respiratory_rate else None,
            weight=float(r.weight) if r.weight else None,
            height=float(r.height) if r.height else None,
            bmi=float(r.bmi) if r.bmi else None,
            steps=r.steps,
            calories_burned=float(r.calories_burned) if r.calories_burned else None,
            activity_minutes=r.activity_minutes,
            sleep_hours=float(r.sleep_hours) if r.sleep_hours else None,
            sleep_quality=r.sleep_quality,
            blood_glucose=float(r.blood_glucose) if r.blood_glucose else None,
            additional_metrics=r.additional_metrics,
            notes=r.notes,
            source=r.source,
            device_id=r.device_id,
            is_verified=r.is_verified,
            recorded_by=r.recorded_by,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]


@router.get("/me/stats", response_model=TelemetryStatsResponse)
async def get_my_telemetry_stats(
    period: str = Query("last_7_days", description="Time period: last_7_days, last_30_days, last_3_months"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get aggregated telemetry statistics for the current patient"""
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for patients"
        )
    try:
        # Get patient record
        patient_query = select(Patient).filter(
            and_(
                Patient.email == current_user.email,
                Patient.clinic_id == current_user.clinic_id
            )
        )
        patient_result = await db.execute(patient_query)
        patient = patient_result.scalar_one_or_none()
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient record not found"
            )
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        if period == "last_7_days":
            start_date = end_date - timedelta(days=7)
        elif period == "last_30_days":
            start_date = end_date - timedelta(days=30)
        elif period == "last_3_months":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=7)
        
        # Build aggregation query
        query = select(
            sql_func.count(PatientTelemetry.id).label('count'),
            sql_func.avg(PatientTelemetry.systolic_bp).label('avg_systolic_bp'),
            sql_func.avg(PatientTelemetry.diastolic_bp).label('avg_diastolic_bp'),
            sql_func.avg(PatientTelemetry.heart_rate).label('avg_heart_rate'),
            sql_func.avg(PatientTelemetry.temperature).label('avg_temperature'),
            sql_func.avg(PatientTelemetry.oxygen_saturation).label('avg_oxygen_saturation'),
            sql_func.avg(PatientTelemetry.weight).label('avg_weight'),
            sql_func.avg(PatientTelemetry.bmi).label('avg_bmi'),
            sql_func.sum(PatientTelemetry.steps).label('total_steps'),
            sql_func.avg(PatientTelemetry.calories_burned).label('avg_calories'),
            sql_func.avg(PatientTelemetry.sleep_hours).label('avg_sleep_hours'),
        ).filter(
            and_(
                PatientTelemetry.patient_id == patient.id,
                PatientTelemetry.measured_at >= start_date,
                PatientTelemetry.measured_at <= end_date
            )
        )
        
        result = await db.execute(query)
        stats = result.first()
        
        if not stats or stats.count == 0:
            return TelemetryStatsResponse(
                period=period,
                patient_id=patient.id,
                record_count=0
            )
        
        return TelemetryStatsResponse(
            period=period,
            patient_id=patient.id,
            average_systolic_bp=float(stats.avg_systolic_bp) if stats.avg_systolic_bp else None,
            average_diastolic_bp=float(stats.avg_diastolic_bp) if stats.avg_diastolic_bp else None,
            average_heart_rate=float(stats.avg_heart_rate) if stats.avg_heart_rate else None,
            average_temperature=float(stats.avg_temperature) if stats.avg_temperature else None,
            average_oxygen_saturation=float(stats.avg_oxygen_saturation) if stats.avg_oxygen_saturation else None,
            average_weight=float(stats.avg_weight) if stats.avg_weight else None,
            average_bmi=float(stats.avg_bmi) if stats.avg_bmi else None,
            total_steps=int(stats.total_steps) if stats.total_steps else None,
            average_calories=float(stats.avg_calories) if stats.avg_calories else None,
            average_sleep_hours=float(stats.avg_sleep_hours) if stats.avg_sleep_hours else None,
            record_count=stats.count or 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching telemetry stats: {str(e)}"
        )


@router.get("/{record_id}", response_model=TelemetryResponse)
async def get_telemetry_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get a specific telemetry record"""
    query = select(PatientTelemetry).filter(
        PatientTelemetry.id == record_id,
        PatientTelemetry.clinic_id == current_user.clinic_id
    )
    
    # Patients can only see their own records
    if current_user.role == UserRole.PATIENT:
        patient_query = select(Patient).filter(
            and_(
                Patient.email == current_user.email,
                Patient.clinic_id == current_user.clinic_id
            )
        )
        patient_result = await db.execute(patient_query)
        patient = patient_result.scalar_one_or_none()
        
        if patient:
            query = query.filter(PatientTelemetry.patient_id == patient.id)
    
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telemetry record not found"
        )
    
    return TelemetryResponse(
        id=record.id,
        patient_id=record.patient_id,
        clinic_id=record.clinic_id,
        measured_at=record.measured_at,
        systolic_bp=float(record.systolic_bp) if record.systolic_bp else None,
        diastolic_bp=float(record.diastolic_bp) if record.diastolic_bp else None,
        heart_rate=float(record.heart_rate) if record.heart_rate else None,
        temperature=float(record.temperature) if record.temperature else None,
        oxygen_saturation=float(record.oxygen_saturation) if record.oxygen_saturation else None,
        respiratory_rate=float(record.respiratory_rate) if record.respiratory_rate else None,
        weight=float(record.weight) if record.weight else None,
        height=float(record.height) if record.height else None,
        bmi=float(record.bmi) if record.bmi else None,
        steps=record.steps,
        calories_burned=float(record.calories_burned) if record.calories_burned else None,
        activity_minutes=record.activity_minutes,
        sleep_hours=float(record.sleep_hours) if record.sleep_hours else None,
        sleep_quality=record.sleep_quality,
        blood_glucose=float(record.blood_glucose) if record.blood_glucose else None,
        additional_metrics=record.additional_metrics,
        notes=record.notes,
        source=record.source,
        device_id=record.device_id,
        is_verified=record.is_verified,
        recorded_by=record.recorded_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.put("/{record_id}", response_model=TelemetryResponse)
async def update_telemetry_record(
    record_id: int,
    update_data: TelemetryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Update a telemetry record"""
    query = select(PatientTelemetry).filter(
        PatientTelemetry.id == record_id,
        PatientTelemetry.clinic_id == current_user.clinic_id
    )
    
    # Patients can only update their own records
    if current_user.role == UserRole.PATIENT:
        patient_query = select(Patient).filter(
            and_(
                Patient.email == current_user.email,
                Patient.clinic_id == current_user.clinic_id
            )
        )
        patient_result = await db.execute(patient_query)
        patient = patient_result.scalar_one_or_none()
        
        if patient:
            query = query.filter(PatientTelemetry.patient_id == patient.id)
    
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telemetry record not found"
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Recalculate BMI if weight or height changed
    if 'weight' in update_dict or 'height' in update_dict:
        weight = update_dict.get('weight') or (float(record.weight) if record.weight else None)
        height = update_dict.get('height') or (float(record.height) if record.height else None)
        
        if weight and height:
            height_m = height / 100.0
            bmi = float(weight / (height_m * height_m))
            update_dict['bmi'] = Decimal(str(bmi))
    
    for key, value in update_dict.items():
        if value is not None and key != 'bmi':
            setattr(record, key, value)
        elif key == 'bmi' and value is not None:
            setattr(record, key, Decimal(str(value)))
    
    await db.commit()
    await db.refresh(record)
    
    return TelemetryResponse(
        id=record.id,
        patient_id=record.patient_id,
        clinic_id=record.clinic_id,
        measured_at=record.measured_at,
        systolic_bp=float(record.systolic_bp) if record.systolic_bp else None,
        diastolic_bp=float(record.diastolic_bp) if record.diastolic_bp else None,
        heart_rate=float(record.heart_rate) if record.heart_rate else None,
        temperature=float(record.temperature) if record.temperature else None,
        oxygen_saturation=float(record.oxygen_saturation) if record.oxygen_saturation else None,
        respiratory_rate=float(record.respiratory_rate) if record.respiratory_rate else None,
        weight=float(record.weight) if record.weight else None,
        height=float(record.height) if record.height else None,
        bmi=float(record.bmi) if record.bmi else None,
        steps=record.steps,
        calories_burned=float(record.calories_burned) if record.calories_burned else None,
        activity_minutes=record.activity_minutes,
        sleep_hours=float(record.sleep_hours) if record.sleep_hours else None,
        sleep_quality=record.sleep_quality,
        blood_glucose=float(record.blood_glucose) if record.blood_glucose else None,
        additional_metrics=record.additional_metrics,
        notes=record.notes,
        source=record.source,
        device_id=record.device_id,
        is_verified=record.is_verified,
        recorded_by=record.recorded_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_telemetry_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Delete a telemetry record"""
    query = select(PatientTelemetry).filter(
        PatientTelemetry.id == record_id,
        PatientTelemetry.clinic_id == current_user.clinic_id
    )
    
    # Patients can only delete their own records
    if current_user.role == UserRole.PATIENT:
        patient_query = select(Patient).filter(
            and_(
                Patient.email == current_user.email,
                Patient.clinic_id == current_user.clinic_id
            )
        )
        patient_result = await db.execute(patient_query)
        patient = patient_result.scalar_one_or_none()
        
        if patient:
            query = query.filter(PatientTelemetry.patient_id == patient.id)
    
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telemetry record not found"
        )
    
    await db.delete(record)
    await db.commit()
    
    return None
