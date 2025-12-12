"""
Admin API endpoints for clinic management and licensing
"""

from datetime import date, timedelta, datetime, timezone
from typing import List, Optional
import secrets
import string
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from app.models import (
    Clinic, User, UserRole as UserRoleEnum, Patient, Appointment,
    Invoice, Payment, ServiceItem, Product, StockMovement, Procedure
)
from app.models.menu import UserRole
from app.models.clinical import ClinicalRecord, Prescription, Diagnosis
from app.schemas.clinic import (
    ClinicCreate, ClinicUpdate, ClinicResponse, ClinicListResponse,
    ClinicLicenseUpdate, ClinicStatsResponse
)
from app.core.auth import get_current_user, RoleChecker
from app.core.security import hash_password
from app.core.licensing import AVAILABLE_MODULES
from typing import Dict, Any
from sqlalchemy.exc import SQLAlchemyError
import asyncio
from app.models import SystemLog
from app.schemas.system_log import (
    SystemLogCreate, SystemLogUpdate, SystemLogResponse,
)
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


def generate_secure_password(length: int = 12) -> str:
    """
    Generate a secure random password that meets basic complexity requirements.
    """
    if length < 10:
        length = 10

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"

    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*()-_=+" for c in pwd)
        ):
            return pwd

router = APIRouter(prefix="/admin", tags=["Admin"])

# Require admin role for all endpoints
require_admin = RoleChecker([UserRoleEnum.ADMIN])


@router.get("/clinics/stats", response_model=ClinicStatsResponse)
async def get_clinic_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get clinic statistics
    """
    # Total clinics
    total_clinics_query = select(func.count(Clinic.id))
    total_result = await db.execute(total_clinics_query)
    total_clinics = total_result.scalar()
    
    # Active clinics
    active_clinics_query = select(func.count(Clinic.id)).filter(Clinic.is_active == True)
    active_result = await db.execute(active_clinics_query)
    active_clinics = active_result.scalar()
    
    # Expired licenses
    expired_query = select(func.count(Clinic.id)).filter(
        and_(
            Clinic.expiration_date.isnot(None),
            Clinic.expiration_date < date.today()
        )
    )
    expired_result = await db.execute(expired_query)
    expired_licenses = expired_result.scalar()
    
    # Total users
    total_users_query = select(func.count(User.id)).filter(User.is_active == True)
    users_result = await db.execute(total_users_query)
    total_users = users_result.scalar()
    
    # Clinics near expiration (next 30 days)
    near_expiration_date = date.today() + timedelta(days=30)
    near_expiration_query = select(func.count(Clinic.id)).filter(
        and_(
            Clinic.expiration_date.isnot(None),
            Clinic.expiration_date <= near_expiration_date,
            Clinic.expiration_date >= date.today()
        )
    )
    near_expiration_result = await db.execute(near_expiration_query)
    clinics_near_expiration = near_expiration_result.scalar()
    
    return ClinicStatsResponse(
        total_clinics=total_clinics,
        active_clinics=active_clinics,
        expired_licenses=expired_licenses,
        total_users=total_users,
        clinics_near_expiration=clinics_near_expiration
    )


@router.get("/clinics", response_model=List[ClinicListResponse])
async def list_clinics(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    license_expired: Optional[bool] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    List all clinics with filtering options
    """
    query = select(Clinic)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Clinic.name.ilike(f"%{search}%"),
                Clinic.legal_name.ilike(f"%{search}%"),
                Clinic.tax_id.ilike(f"%{search}%"),
                Clinic.email.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.filter(Clinic.is_active == is_active)
    
    if license_expired is not None:
        if license_expired:
            query = query.filter(
                and_(
                    Clinic.expiration_date.isnot(None),
                    Clinic.expiration_date < date.today()
                )
            )
        else:
            query = query.filter(
                or_(
                    Clinic.expiration_date.isnull(),
                    Clinic.expiration_date >= date.today()
                )
            )
    
    # Get total count
    count_query = select(func.count(Clinic.id))
    for filter_condition in query.whereclause.children if query.whereclause else []:
        count_query = count_query.where(filter_condition)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Clinic.created_at.desc())
    
    result = await db.execute(query)
    clinics = result.scalars().all()
    
    # Get user counts for each clinic
    clinic_list = []
    for clinic in clinics:
        user_count_query = select(func.count(User.id)).filter(
            User.clinic_id == clinic.id,
            User.is_active == True
        )
        user_count_result = await db.execute(user_count_query)
        user_count = user_count_result.scalar()
        
        clinic_list.append(ClinicListResponse(
            id=clinic.id,
            name=clinic.name,
            legal_name=clinic.legal_name,
            tax_id=clinic.tax_id,
            email=clinic.email,
            is_active=clinic.is_active,
            license_key=clinic.license_key,
            expiration_date=clinic.expiration_date,
            max_users=clinic.max_users,
            active_modules=clinic.active_modules or [],
            user_count=user_count,
            created_at=clinic.created_at.date()
        ))
    
    return clinic_list


@router.get("/clinics/me", response_model=ClinicResponse)
async def get_my_clinic(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get the current user's clinic information
    Available to any authenticated user
    """
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not associated with a clinic"
        )
    
    query = select(Clinic).filter(Clinic.id == current_user.clinic_id)
    result = await db.execute(query)
    clinic = result.scalar_one_or_none()
    
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    
    # Ensure date-only fields for pydantic schema
    from datetime import date as date_type, datetime
    
    # Helper function to convert datetime to date - absolutely ensure it's a date object
    def to_date(dt_value):
        """Convert datetime or date to pure date object - guaranteed"""
        if dt_value is None:
            return None
        if isinstance(dt_value, date_type):
            # Already a date, return as-is
            return dt_value
        if isinstance(dt_value, datetime):
            # For timezone-aware datetimes, convert to UTC first
            if dt_value.tzinfo is not None:
                from datetime import timezone as tz
                dt_value = dt_value.astimezone(tz.utc)
            # Create a NEW date object from the datetime components
            # This ensures we have a pure date object, not a datetime
            return date_type(dt_value.year, dt_value.month, dt_value.day)
        # Fallback: try to get date attribute
        if hasattr(dt_value, 'date'):
            dt_result = dt_value.date()
            # If date() returns a datetime (shouldn't happen), convert it
            if isinstance(dt_result, datetime):
                if dt_result.tzinfo is not None:
                    from datetime import timezone as tz
                    dt_result = dt_result.astimezone(tz.utc)
                return date_type(dt_result.year, dt_result.month, dt_result.day)
            # If it's already a date, create a new one to be sure
            if isinstance(dt_result, date_type):
                return date_type(dt_result.year, dt_result.month, dt_result.day)
        # Last resort
        return date_type.today()
    
    # Convert datetime to date for created_at - access directly and convert immediately
    created_at_raw = clinic.created_at if hasattr(clinic, 'created_at') and clinic.created_at is not None else None
    # Force immediate conversion - don't trust any intermediate values
    if created_at_raw is None:
        created_at_date = date_type.today()
    elif isinstance(created_at_raw, datetime):
        # It's a datetime - convert to UTC if timezone-aware, then extract date
        if created_at_raw.tzinfo is not None:
            from datetime import timezone as tz
            created_at_raw = created_at_raw.astimezone(tz.utc)
        created_at_date = date_type(created_at_raw.year, created_at_raw.month, created_at_raw.day)
    elif isinstance(created_at_raw, date_type):
        # Already a date - create new instance to be absolutely sure
        created_at_date = date_type(created_at_raw.year, created_at_raw.month, created_at_raw.day)
    else:
        # Fallback
        created_at_date = date_type.today()
    
    # Convert datetime to date for updated_at - same approach
    updated_at_raw = clinic.updated_at if hasattr(clinic, 'updated_at') and clinic.updated_at is not None else None
    if updated_at_raw is None:
        updated_at_date = None
    elif isinstance(updated_at_raw, datetime):
        # It's a datetime - convert to UTC if timezone-aware, then extract date
        if updated_at_raw.tzinfo is not None:
            from datetime import timezone as tz
            updated_at_raw = updated_at_raw.astimezone(tz.utc)
        updated_at_date = date_type(updated_at_raw.year, updated_at_raw.month, updated_at_raw.day)
    elif isinstance(updated_at_raw, date_type):
        # Already a date - create new instance to be absolutely sure
        updated_at_date = date_type(updated_at_raw.year, updated_at_raw.month, updated_at_raw.day)
    else:
        updated_at_date = None
    
    # Verify conversion worked - ensure we have pure date objects (not datetime)
    # This is critical for Pydantic v2 validation
    if not isinstance(created_at_date, date_type) or isinstance(created_at_date, datetime):
        # Force conversion if somehow it's still a datetime
        if isinstance(created_at_date, datetime):
            if created_at_date.tzinfo is not None:
                from datetime import timezone as tz
                created_at_date = created_at_date.astimezone(tz.utc)
            created_at_date = date_type(created_at_date.year, created_at_date.month, created_at_date.day)
        else:
            created_at_date = date_type.today()
    
    if updated_at_date is not None and (not isinstance(updated_at_date, date_type) or isinstance(updated_at_date, datetime)):
        # Force conversion if somehow it's still a datetime
        if isinstance(updated_at_date, datetime):
            if updated_at_date.tzinfo is not None:
                from datetime import timezone as tz
                updated_at_date = updated_at_date.astimezone(tz.utc)
            updated_at_date = date_type(updated_at_date.year, updated_at_date.month, updated_at_date.day)
        else:
            updated_at_date = None
    
    # Build response as dict to ensure proper date conversion
    response_dict = {
        "id": clinic.id,
        "name": clinic.name,
        "legal_name": clinic.legal_name,
        "tax_id": clinic.tax_id,
        "address": clinic.address,
        "phone": clinic.phone,
        "email": clinic.email,
        "is_active": clinic.is_active,
        "license_key": clinic.license_key,
        "expiration_date": clinic.expiration_date,
        "max_users": clinic.max_users,
        "active_modules": clinic.active_modules or [],
        "created_at": created_at_date,
        "updated_at": updated_at_date,
    }
    
    # Double-check: ensure we have pure date objects (not datetime)
    # This is critical - Pydantic v2 is very strict about date vs datetime
    if isinstance(response_dict.get('created_at'), datetime):
        dt = response_dict['created_at']
        if dt.tzinfo is not None:
            from datetime import timezone as tz
            dt = dt.astimezone(tz.utc)
        response_dict['created_at'] = date_type(dt.year, dt.month, dt.day)
    
    if isinstance(response_dict.get('updated_at'), datetime):
        dt = response_dict['updated_at']
        if dt is not None:
            if dt.tzinfo is not None:
                from datetime import timezone as tz
                dt = dt.astimezone(tz.utc)
            response_dict['updated_at'] = date_type(dt.year, dt.month, dt.day)
    
    # Final verification - these MUST be date objects, not datetime
    assert isinstance(response_dict['created_at'], date_type) and not isinstance(response_dict['created_at'], datetime), \
        f"created_at is {type(response_dict['created_at'])} - must be date, not datetime"
    if response_dict.get('updated_at') is not None:
        assert isinstance(response_dict['updated_at'], date_type) and not isinstance(response_dict['updated_at'], datetime), \
            f"updated_at is {type(response_dict['updated_at'])} - must be date, not datetime"
    
    # Use model_construct to create the response object (bypasses validation)
    # Since we've manually converted everything to date objects, this is safe
    # model_construct doesn't validate, so it won't complain about datetime objects
    # But we've already converted them, so we're good
    return ClinicResponse.model_construct(**response_dict)


@router.put("/clinics/me", response_model=ClinicResponse)
async def update_my_clinic(
    clinic_data: ClinicUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update the current user's clinic information
    Available to admin users (AdminClinica role) or super admin
    """
    # Check if user has permission (admin role or super admin)
    if current_user.role not in [UserRoleEnum.ADMIN] and current_user.role_id != 2:  # AdminClinica role_id is 2
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinic administrators can update clinic information"
        )
    
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not associated with a clinic"
        )
    
    query = select(Clinic).filter(Clinic.id == current_user.clinic_id)
    result = await db.execute(query)
    clinic = result.scalar_one_or_none()
    
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    
    # Check if tax_id is unique (if being updated)
    if clinic_data.tax_id and clinic_data.tax_id != clinic.tax_id:
        existing_clinic = await db.execute(
            select(Clinic).filter(Clinic.tax_id == clinic_data.tax_id)
        )
        if existing_clinic.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Clinic with this tax ID already exists"
            )
    
    # Check if license_key is unique (if being updated)
    if clinic_data.license_key and clinic_data.license_key != clinic.license_key:
        existing_license = await db.execute(
            select(Clinic).filter(Clinic.license_key == clinic_data.license_key)
        )
        if existing_license.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License key already exists"
            )
    
    # Update clinic (only allow updating basic info, not license info for clinic admins)
    update_data = clinic_data.model_dump(exclude_unset=True)
    # Remove license-related fields for clinic admins (only super admin can update these)
    if current_user.role != UserRoleEnum.ADMIN or current_user.role_id != 1:  # Not super admin
        update_data.pop("license_key", None)
        update_data.pop("expiration_date", None)
        update_data.pop("max_users", None)
        update_data.pop("active_modules", None)
    
    for field, value in update_data.items():
        setattr(clinic, field, value)
    
    await db.commit()
    await db.refresh(clinic)
    
    # Ensure date-only fields for pydantic schema
    from datetime import date as date_type, datetime
    
    # Helper function to convert datetime to date - absolutely ensure it's a date object
    def to_date(dt_value):
        """Convert datetime or date to pure date object - guaranteed"""
        if dt_value is None:
            return None
        if isinstance(dt_value, date_type):
            # Already a date, return as-is
            return dt_value
        if isinstance(dt_value, datetime):
            # For timezone-aware datetimes, convert to UTC first
            if dt_value.tzinfo is not None:
                from datetime import timezone as tz
                dt_value = dt_value.astimezone(tz.utc)
            # Create a NEW date object from the datetime components
            # This ensures we have a pure date object, not a datetime
            return date_type(dt_value.year, dt_value.month, dt_value.day)
        # Fallback: try to get date attribute
        if hasattr(dt_value, 'date'):
            dt_result = dt_value.date()
            # If date() returns a datetime (shouldn't happen), convert it
            if isinstance(dt_result, datetime):
                if dt_result.tzinfo is not None:
                    from datetime import timezone as tz
                    dt_result = dt_result.astimezone(tz.utc)
                return date_type(dt_result.year, dt_result.month, dt_result.day)
            # If it's already a date, create a new one to be sure
            if isinstance(dt_result, date_type):
                return date_type(dt_result.year, dt_result.month, dt_result.day)
        # Last resort
        return date_type.today()
    
    # Convert datetime to date for created_at - access directly and convert immediately
    created_at_raw = clinic.created_at if hasattr(clinic, 'created_at') and clinic.created_at is not None else None
    # Force immediate conversion - don't trust any intermediate values
    if created_at_raw is None:
        created_at_date = date_type.today()
    elif isinstance(created_at_raw, datetime):
        # It's a datetime - convert to UTC if timezone-aware, then extract date
        if created_at_raw.tzinfo is not None:
            from datetime import timezone as tz
            created_at_raw = created_at_raw.astimezone(tz.utc)
        created_at_date = date_type(created_at_raw.year, created_at_raw.month, created_at_raw.day)
    elif isinstance(created_at_raw, date_type):
        # Already a date - create new instance to be absolutely sure
        created_at_date = date_type(created_at_raw.year, created_at_raw.month, created_at_raw.day)
    else:
        # Fallback
        created_at_date = date_type.today()
    
    # Convert datetime to date for updated_at - same approach
    updated_at_raw = clinic.updated_at if hasattr(clinic, 'updated_at') and clinic.updated_at is not None else None
    if updated_at_raw is None:
        updated_at_date = None
    elif isinstance(updated_at_raw, datetime):
        # It's a datetime - convert to UTC if timezone-aware, then extract date
        if updated_at_raw.tzinfo is not None:
            from datetime import timezone as tz
            updated_at_raw = updated_at_raw.astimezone(tz.utc)
        updated_at_date = date_type(updated_at_raw.year, updated_at_raw.month, updated_at_raw.day)
    elif isinstance(updated_at_raw, date_type):
        # Already a date - create new instance to be absolutely sure
        updated_at_date = date_type(updated_at_raw.year, updated_at_raw.month, updated_at_raw.day)
    else:
        updated_at_date = None
    
    # Verify conversion worked - ensure we have pure date objects (not datetime)
    # This is critical for Pydantic v2 validation
    if not isinstance(created_at_date, date_type) or isinstance(created_at_date, datetime):
        # Force conversion if somehow it's still a datetime
        if isinstance(created_at_date, datetime):
            if created_at_date.tzinfo is not None:
                from datetime import timezone as tz
                created_at_date = created_at_date.astimezone(tz.utc)
            created_at_date = date_type(created_at_date.year, created_at_date.month, created_at_date.day)
        else:
            created_at_date = date_type.today()
    
    if updated_at_date is not None and (not isinstance(updated_at_date, date_type) or isinstance(updated_at_date, datetime)):
        # Force conversion if somehow it's still a datetime
        if isinstance(updated_at_date, datetime):
            if updated_at_date.tzinfo is not None:
                from datetime import timezone as tz
                updated_at_date = updated_at_date.astimezone(tz.utc)
            updated_at_date = date_type(updated_at_date.year, updated_at_date.month, updated_at_date.day)
        else:
            updated_at_date = None
    
    # Build response as dict to ensure proper date conversion
    response_dict = {
        "id": clinic.id,
        "name": clinic.name,
        "legal_name": clinic.legal_name,
        "tax_id": clinic.tax_id,
        "address": clinic.address,
        "phone": clinic.phone,
        "email": clinic.email,
        "is_active": clinic.is_active,
        "license_key": clinic.license_key,
        "expiration_date": clinic.expiration_date,
        "max_users": clinic.max_users,
        "active_modules": clinic.active_modules or [],
        "created_at": created_at_date,
        "updated_at": updated_at_date,
    }
    
    # Double-check: ensure we have pure date objects (not datetime)
    # This is critical - Pydantic v2 is very strict about date vs datetime
    if isinstance(response_dict.get('created_at'), datetime):
        dt = response_dict['created_at']
        if dt.tzinfo is not None:
            from datetime import timezone as tz
            dt = dt.astimezone(tz.utc)
        response_dict['created_at'] = date_type(dt.year, dt.month, dt.day)
    
    if isinstance(response_dict.get('updated_at'), datetime):
        dt = response_dict['updated_at']
        if dt is not None:
            if dt.tzinfo is not None:
                from datetime import timezone as tz
                dt = dt.astimezone(tz.utc)
            response_dict['updated_at'] = date_type(dt.year, dt.month, dt.day)
    
    # Final verification - these MUST be date objects, not datetime
    assert isinstance(response_dict['created_at'], date_type) and not isinstance(response_dict['created_at'], datetime), \
        f"created_at is {type(response_dict['created_at'])} - must be date, not datetime"
    if response_dict.get('updated_at') is not None:
        assert isinstance(response_dict['updated_at'], date_type) and not isinstance(response_dict['updated_at'], datetime), \
            f"updated_at is {type(response_dict['updated_at'])} - must be date, not datetime"
    
    # Use model_construct to create the response object (bypasses validation)
    # Since we've manually converted everything to date objects, this is safe
    # model_construct doesn't validate, so it won't complain about datetime objects
    # But we've already converted them, so we're good
    return ClinicResponse.model_construct(**response_dict)


@router.get("/clinics/{clinic_id}", response_model=ClinicResponse)
async def get_clinic(
    clinic_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get a specific clinic by ID
    """
    query = select(Clinic).filter(Clinic.id == clinic_id)
    result = await db.execute(query)
    clinic = result.scalar_one_or_none()
    
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    
    # Ensure date-only fields for pydantic schema - use same conversion as /me endpoint
    from datetime import date as date_type, datetime
    
    def to_date(dt_value):
        """Convert datetime or date to pure date object - guaranteed"""
        if dt_value is None:
            return None
        if isinstance(dt_value, date_type):
            return date_type(dt_value.year, dt_value.month, dt_value.day)
        if isinstance(dt_value, datetime):
            if dt_value.tzinfo is not None:
                from datetime import timezone as tz
                dt_value = dt_value.astimezone(tz.utc)
            return date_type(dt_value.year, dt_value.month, dt_value.day)
        if hasattr(dt_value, 'date'):
            dt_result = dt_value.date()
            if isinstance(dt_result, datetime):
                if dt_result.tzinfo is not None:
                    from datetime import timezone as tz
                    dt_result = dt_result.astimezone(tz.utc)
                return date_type(dt_result.year, dt_result.month, dt_result.day)
            if isinstance(dt_result, date_type):
                return date_type(dt_result.year, dt_result.month, dt_result.day)
        return date_type.today()
    
    response_dict = {
        "id": clinic.id,
        "name": clinic.name,
        "legal_name": clinic.legal_name,
        "tax_id": clinic.tax_id,
        "address": clinic.address,
        "phone": clinic.phone,
        "email": clinic.email,
        "is_active": clinic.is_active,
        "license_key": clinic.license_key,
        "expiration_date": clinic.expiration_date,
        "max_users": clinic.max_users,
        "active_modules": clinic.active_modules or [],
        "created_at": to_date(getattr(clinic, "created_at", None)) or date_type.today(),
        "updated_at": to_date(getattr(clinic, "updated_at", None)),
    }
    
    try:
        return ClinicResponse.model_validate(response_dict)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"ClinicResponse validation failed: {e}")
        return ClinicResponse.model_construct(**response_dict)


@router.post("/clinics")  # Removed response_model to allow admin_user field
async def create_clinic(
    clinic_data: ClinicCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a new clinic
    """
    # Run initial checks in parallel for better performance
    tax_id_check = select(Clinic).filter(Clinic.tax_id == clinic_data.tax_id)
    license_check = select(Clinic).filter(Clinic.license_key == clinic_data.license_key) if clinic_data.license_key else None
    admin_role_check = select(UserRole).where(UserRole.name == "AdminClinica")
    
    # Execute checks in parallel
    tasks = [db.execute(tax_id_check), db.execute(admin_role_check)]
    if license_check:
        tasks.append(db.execute(license_check))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check tax_id
    existing_clinic_result = results[0]
    if isinstance(existing_clinic_result, Exception):
        logger.error(f"Error checking tax_id: {existing_clinic_result}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking clinic tax ID"
        )
    if existing_clinic_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clinic with this tax ID already exists"
        )
    
    # Check license_key if provided
    if clinic_data.license_key:
        license_result = results[2] if len(results) > 2 else None
        if isinstance(license_result, Exception):
            logger.error(f"Error checking license_key: {license_result}")
        elif license_result and license_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License key already exists"
            )
    
    # Get AdminClinica role
    admin_role_result = results[1]
    if isinstance(admin_role_result, Exception):
        logger.error(f"Error fetching AdminClinica role: {admin_role_result}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching admin role"
        )
    admin_role = admin_role_result.scalar_one_or_none()
    
    if not admin_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AdminClinica role not found. Please run seed script first."
        )
    
    # Create clinic
    clinic = Clinic(**clinic_data.model_dump())
    db.add(clinic)
    await db.flush()  # Flush to get clinic.id without committing
    
    # Generate default admin user credentials
    # Use clinic name to create username (sanitized)
    clinic_name_slug = clinic_data.name.lower().replace(" ", "_").replace("-", "_")
    # Remove special characters, keep only alphanumeric and underscore
    clinic_name_slug = "".join(c for c in clinic_name_slug if c.isalnum() or c == "_")
    # Limit length and ensure uniqueness
    base_username = f"admin_{clinic_name_slug[:20]}"
    
    # Check if username already exists, if so append clinic id
    # Use clinic.id to make username unique from the start
    username = f"{base_username}_{clinic.id}"
    # Verify it doesn't exist (shouldn't, but check anyway)
    existing_user_check = await db.execute(
        select(User).where(User.username == username)
    )
    if existing_user_check.scalar_one_or_none():
        # If by some chance it exists, append timestamp
        import time
        username = f"{base_username}_{clinic.id}_{int(time.time())}"
    
    # Generate email from clinic email or use default pattern
    # Use clinic email if available, otherwise generate from clinic name
    admin_email = clinic_data.email if clinic_data.email else f"admin@{clinic_name_slug}.com"
    # Use clinic.id to make email unique from the start
    if "@" in admin_email:
        local, domain = admin_email.split("@", 1)
        admin_email = f"{local}_{clinic.id}@{domain}"
    else:
        admin_email = f"admin_{clinic.id}@{clinic_name_slug}.com"
    
    # Verify email doesn't exist (shouldn't, but check anyway)
    existing_email_check = await db.execute(
        select(User).where(User.email == admin_email)
    )
    if existing_email_check.scalar_one_or_none():
        # If by some chance it exists, append timestamp
        import time
        if "@" in admin_email:
            local, domain = admin_email.split("@", 1)
            admin_email = f"{local}_{int(time.time())}@{domain}"
        else:
            admin_email = f"admin_{clinic.id}_{int(time.time())}@{clinic_name_slug}.com"
    
    # Generate secure random password for the clinic admin user (16 characters for better security)
    default_password = generate_secure_password(length=16)
    
    # Create AdminClinica user for the new clinic
    admin_user = User(
        username=username,
        email=admin_email,
        hashed_password=hash_password(default_password),
        first_name="Administrador",
        last_name=clinic_data.name,
        role=UserRoleEnum.ADMIN,  # Legacy enum
        role_id=admin_role.id,  # AdminClinica role_id = 2
        clinic_id=clinic.id,
        is_active=True,
        is_verified=True,  # Auto-verify the admin user
    )
    db.add(admin_user)
    
    # Commit both clinic and user
    await db.commit()
    await db.refresh(clinic)
    await db.refresh(admin_user)
    
    # Send credentials email in background (non-blocking)
    recipient_email = clinic.email or admin_email
    if recipient_email:
        # Create a background task to send email
        async def send_clinic_admin_email():
            try:
                logger.info(f"Attempting to send clinic admin credentials email. Recipient: {recipient_email}, Email service enabled: {email_service.is_enabled()}")
                # Get the frontend URL from environment or use default
                frontend_url = os.getenv("FRONTEND_URL", "https://prontivus-frontend-p2rr.vercel.app")
                login_url = f"{frontend_url}/portal/login"
                logger.info(f"Preparing email with login URL: {login_url}")
                
                # Professional HTML email with credentials
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
                        .credentials {{ background-color: white; padding: 20px; margin: 20px 0; border-left: 4px solid #0F4C75; }}
                        .credential-item {{ margin: 10px 0; padding: 8px; background-color: #f5f5f5; border-radius: 3px; }}
                        .credential-label {{ font-weight: bold; color: #0F4C75; }}
                        .password {{ font-family: monospace; font-size: 14px; color: #d32f2f; background-color: #fff3cd; padding: 5px 10px; border-radius: 3px; }}
                        .button {{ display: inline-block; padding: 12px 24px; background-color: #0F4C75; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                        .warning {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Bem-vindo ao Prontivus</h1>
                        </div>
                        <div class="content">
                            <p>Olá,</p>
                            <p>Sua clínica <strong>{clinic.name}</strong> foi cadastrada com sucesso no sistema Prontivus.</p>
                            
                            <p>Segue abaixo as credenciais do usuário administrador da clínica:</p>
                            
                            <div class="credentials">
                                <div class="credential-item">
                                    <span class="credential-label">Usuário:</span> {username}
                                </div>
                                <div class="credential-item">
                                    <span class="credential-label">E-mail:</span> {admin_email}
                                </div>
                                <div class="credential-item">
                                    <span class="credential-label">Senha provisória:</span>
                                    <div class="password">{default_password}</div>
                                </div>
                            </div>
                            
                            <div class="warning">
                                <strong>⚠️ Importante:</strong> Por segurança, recomendamos fortemente que você altere esta senha no primeiro acesso ao sistema.
                            </div>
                            
                            <p style="text-align: center;">
                                <a href="{login_url}" class="button">Acessar o Sistema</a>
                            </p>
                            
                            <p>Ou copie e cole o seguinte link no seu navegador:</p>
                            <p style="word-break: break-all; color: #0F4C75;">{login_url}</p>
                        </div>
                        <div class="footer">
                            <p>Atenciosamente,<br/><strong>Equipe Prontivus</strong></p>
                            <p style="margin-top: 20px; font-size: 11px; color: #999;">
                                Este é um e-mail automático. Por favor, não responda a esta mensagem.
                            </p>
                        </div>
                    </div>
                </body>
                </html>
                """
                text_body = (
                    f"Bem-vindo ao Prontivus\n\n"
                    f"Olá,\n\n"
                    f"Sua clínica {clinic.name} foi cadastrada com sucesso no sistema Prontivus.\n\n"
                    f"CREDENCIAIS DO ADMINISTRADOR:\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Usuário: {username}\n"
                    f"E-mail: {admin_email}\n"
                    f"Senha provisória: {default_password}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"⚠️ IMPORTANTE: Por segurança, recomendamos fortemente que você altere esta senha no primeiro acesso ao sistema.\n\n"
                    f"Acesse o sistema em: {login_url}\n\n"
                    f"Atenciosamente,\nEquipe Prontivus\n\n"
                    f"---\n"
                    f"Este é um e-mail automático. Por favor, não responda a esta mensagem."
                )
                email_sent = await email_service.send_email(
                    to_email=recipient_email,
                    subject="Prontivus - Credenciais de Acesso do Administrador",
                    html_body=html_body,
                    text_body=text_body,
                )
                if email_sent:
                    logger.info(f"Clinic admin credentials email sent successfully to {recipient_email}")
                else:
                    logger.warning(f"Failed to send clinic admin credentials email to {recipient_email} - email service returned False")
            except Exception as e:
                # Don't fail clinic creation if email sending fails, but log the error
                logger.exception(f"Exception occurred while sending clinic admin credentials email to {recipient_email}: {str(e)}")
        
        background_tasks.add_task(send_clinic_admin_email)
        logger.info(f"Email sending task added to background for clinic {clinic.id}")
    else:
        logger.warning(f"No recipient email available for clinic {clinic.id}. Clinic email: {clinic.email}, Admin email: {admin_email}")
    
    # Log the creation
    try:
        log_entry = SystemLog(
            clinic_id=clinic.id,
            user_id=current_user.id if current_user else None,
            action="clinic_created",
            details={
                "clinic_id": clinic.id,
                "clinic_name": clinic.name,
                "admin_user_created": True,
                "admin_username": username,
                "admin_email": admin_email,
            },
            severity="INFO"
        )
        db.add(log_entry)
        await db.commit()
    except Exception as e:
        # Don't fail clinic creation if logging fails
        print(f"Warning: Failed to log clinic creation: {e}")
    
    # Build response with admin user info
    def to_date(dt_value):
        if dt_value is None:
            return None
        if isinstance(dt_value, date):
            return dt_value
        if isinstance(dt_value, datetime):
            if dt_value.tzinfo is not None:
                dt_value = dt_value.astimezone(timezone.utc)
            return date(dt_value.year, dt_value.month, dt_value.day)
        return date.today()
    
    response_dict = {
        "id": clinic.id,
        "name": clinic.name,
        "legal_name": clinic.legal_name,
        "tax_id": clinic.tax_id,
        "address": clinic.address,
        "phone": clinic.phone,
        "email": clinic.email,
        "is_active": clinic.is_active,
        "license_key": clinic.license_key,
        "expiration_date": clinic.expiration_date,
        "max_users": clinic.max_users,
        "active_modules": clinic.active_modules or [],
        "created_at": to_date(getattr(clinic, "created_at", None)) or date.today(),
        "updated_at": to_date(getattr(clinic, "updated_at", None)),
        # Add admin user info to response (password NOT included for security)
        "admin_user": {
            "username": username,
            "email": admin_email,
            "role": "AdminClinica"
        }
    }
    
    # Return as dict to bypass Pydantic validation for admin_user field
    # FastAPI will serialize it correctly
    return response_dict


@router.put("/clinics/{clinic_id}", response_model=ClinicResponse)
async def update_clinic(
    clinic_id: int,
    clinic_data: ClinicUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update a clinic
    """
    query = select(Clinic).filter(Clinic.id == clinic_id)
    result = await db.execute(query)
    clinic = result.scalar_one_or_none()
    
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    
    # Check if tax_id is unique (if being updated)
    if clinic_data.tax_id and clinic_data.tax_id != clinic.tax_id:
        existing_clinic = await db.execute(
            select(Clinic).filter(Clinic.tax_id == clinic_data.tax_id)
        )
        if existing_clinic.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Clinic with this tax ID already exists"
            )
    
    # Check if license_key is unique (if being updated)
    if clinic_data.license_key and clinic_data.license_key != clinic.license_key:
        existing_license = await db.execute(
            select(Clinic).filter(Clinic.license_key == clinic_data.license_key)
        )
        if existing_license.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License key already exists"
            )
    
    # Update clinic
    update_data = clinic_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clinic, field, value)
    
    await db.commit()
    await db.refresh(clinic)
    
    return clinic


@router.patch("/clinics/{clinic_id}/license", response_model=ClinicResponse)
async def update_clinic_license(
    clinic_id: int,
    license_data: ClinicLicenseUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update clinic license information
    """
    query = select(Clinic).filter(Clinic.id == clinic_id)
    result = await db.execute(query)
    clinic = result.scalar_one_or_none()
    
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    
    # Check if license_key is unique (if being updated)
    if license_data.license_key and license_data.license_key != clinic.license_key:
        existing_license = await db.execute(
            select(Clinic).filter(Clinic.license_key == license_data.license_key)
        )
        if existing_license.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License key already exists"
            )
    
    # Update license information
    update_data = license_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clinic, field, value)
    
    await db.commit()
    await db.refresh(clinic)
    
    return clinic


@router.delete("/clinics/{clinic_id}")
async def delete_clinic(
    clinic_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Delete a clinic from the database (hard delete).
    This will also delete all related records (users, patients, appointments, etc.)
    due to cascade relationships.
    """
    query = select(Clinic).filter(Clinic.id == clinic_id)
    result = await db.execute(query)
    clinic = result.scalar_one_or_none()
    
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    
    # Prevent deletion of default clinic (ID 1) or clinic with SuperAdmin users
    if clinic_id == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir a clínica padrão do sistema."
        )
    
    # Check if this clinic has SuperAdmin users
    superadmin_query = select(User).filter(
        User.clinic_id == clinic_id,
        User.role == "admin",
        User.role_id == 1  # SuperAdmin role_id
    )
    superadmin_result = await db.execute(superadmin_query)
    superadmin_users = superadmin_result.scalars().all()
    
    if superadmin_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir uma clínica que possui usuários SuperAdmin. Remova os usuários SuperAdmin antes de excluir a clínica."
        )
    
    # Store clinic info for logging before deletion
    clinic_name = clinic.name
    clinic_id_for_log = clinic.id
    deleted_by = current_user.username if current_user else "system"
    
    # Use SQL directly to delete all related records, then delete clinic
    # This avoids ORM relationship loading issues and transaction problems
    from sqlalchemy import text
    
    try:
        # Delete related records using SQL to avoid ORM issues
        # Order matters: delete child records before parent records
        
        # Delete all related records using SQL to avoid ORM relationship issues
        # This approach is more reliable and avoids transaction abort problems
        
        # Helper function to execute DELETE with error handling
        async def safe_delete(query: str, params: dict, table_name: str = "", optional: bool = False):
            """Execute DELETE query, handling errors gracefully"""
            try:
                logger.info(f"Attempting to delete from {table_name} for clinic {clinic_id}")
                await db.execute(text(query), params)
                logger.info(f"Successfully deleted from {table_name} for clinic {clinic_id}")
            except Exception as e:
                error_msg = str(e).lower()
                logger.warning(f"Error deleting from {table_name}: {error_msg}")
                # If table doesn't exist and it's optional, just continue
                if optional and ("does not exist" in error_msg or "undefinedtable" in error_msg or "table" in error_msg and "doesn't exist" in error_msg):
                    logger.info(f"Table {table_name} does not exist, skipping (optional)")
                    return  # Table doesn't exist, skip
                # If transaction is aborted, rollback and re-raise immediately
                if "aborted" in error_msg or "in failed sql transaction" in error_msg:
                    await db.rollback()
                    logger.error(f"Transaction aborted while deleting {table_name}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Erro ao processar exclusão de {table_name}. A operação foi interrompida. Por favor, tente novamente."
                    )
                # For foreign key errors, provide a user-friendly message
                if "foreign key" in error_msg or "constraint" in error_msg or "violates foreign key" in error_msg or "cannot delete" in error_msg:
                    await db.rollback()
                    logger.error(f"Foreign key constraint error while deleting {table_name}: {error_msg}")
                    # This will be caught by the outer exception handler which has better messaging
                    raise
                # For other errors, log and re-raise (will be caught by outer handler)
                logger.error(f"Unexpected error deleting from {table_name}: {error_msg}")
                await db.rollback()
                raise
        
        # Delete in correct order to respect foreign key constraints
        # 1. Delete clinical records, prescriptions, diagnoses first (they reference appointments)
        # These are optional tables that might not exist, so we handle errors gracefully
        # Use a helper function that checks for transaction abort and handles it properly
        async def safe_delete_optional(query: str, params: dict, table_name: str):
            """Delete from optional table, handling errors gracefully - skip if table doesn't exist"""
            try:
                logger.info(f"Attempting to delete from optional table {table_name} for clinic {clinic_id}")
                await db.execute(text(query), params)
                logger.info(f"Successfully deleted from optional table {table_name} for clinic {clinic_id}")
            except Exception as e:
                error_msg = str(e).lower()
                logger.warning(f"Error deleting from optional table {table_name}: {error_msg}")
                # If table doesn't exist, MySQL/PostgreSQL may abort the transaction
                # We need to rollback and restart the transaction
                if ("does not exist" in error_msg or "undefinedtable" in error_msg or 
                    "table" in error_msg and "doesn't exist" in error_msg or
                    "unknown table" in error_msg):
                    # Rollback to clear the aborted transaction
                    logger.info(f"Optional table {table_name} does not exist, skipping")
                    try:
                        await db.rollback()
                        # Restart transaction by executing a simple query
                        await db.execute(text("SELECT 1"))
                    except Exception as rollback_error:
                        logger.warning(f"Error during rollback/restart: {rollback_error}")
                    return  # Table doesn't exist, skip
                # Handle "unknown column" errors - table exists but schema is different
                if "unknown column" in error_msg:
                    logger.warning(f"Optional table {table_name} has different schema (unknown column), skipping")
                    try:
                        await db.rollback()
                        # Restart transaction by executing a simple query
                        await db.execute(text("SELECT 1"))
                    except Exception as rollback_error:
                        logger.warning(f"Error during rollback/restart: {rollback_error}")
                    return  # Column doesn't exist, skip this deletion
                # If transaction is aborted for other reasons, rollback and re-raise
                if "aborted" in error_msg or "in failed sql transaction" in error_msg:
                    await db.rollback()
                    # Restart transaction
                    await db.execute(text("SELECT 1"))
                    logger.error(f"Transaction aborted while deleting optional table {table_name}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Erro ao deletar {table_name}: Transação abortada. Erro: {str(e)}"
                    )
                # For foreign key errors, log and re-raise
                if "foreign key" in error_msg or "constraint" in error_msg:
                    logger.error(f"Foreign key constraint error while deleting optional table {table_name}: {error_msg}")
                    await db.rollback()
                    raise
                # For any other error, log and re-raise to be handled by outer exception handler
                logger.error(f"Unexpected error deleting from optional table {table_name}: {error_msg}")
                await db.rollback()
                raise
        
        # PHASE 1: Delete all optional tables first (these may cause ROLLBACK if they don't exist)
        # This ensures that if there's a ROLLBACK, we haven't lost any critical operations yet
        
        # Delete records that reference appointments (must be deleted before appointments)
        # These are optional tables that might not exist
        # Note: prescriptions and diagnoses reference clinical_records, not appointments directly
        # So we need to delete them through clinical_records first
        
        # First, delete prescriptions that reference clinical_records linked to appointments
        # Using JOIN syntax for MySQL compatibility (some MySQL versions don't allow subqueries in DELETE)
        await safe_delete_optional("""
            DELETE p FROM prescriptions p
            INNER JOIN clinical_records cr ON p.clinical_record_id = cr.id
            INNER JOIN appointments a ON cr.appointment_id = a.id
            WHERE a.clinic_id = :clinic_id
        """, {"clinic_id": clinic_id}, "prescriptions")
        
        # Then delete diagnoses that reference clinical_records linked to appointments
        await safe_delete_optional("""
            DELETE d FROM diagnoses d
            INNER JOIN clinical_records cr ON d.clinical_record_id = cr.id
            INNER JOIN appointments a ON cr.appointment_id = a.id
            WHERE a.clinic_id = :clinic_id
        """, {"clinic_id": clinic_id}, "diagnoses")
        
        # Finally, delete clinical_records that reference appointments
        await safe_delete_optional("""
            DELETE cr FROM clinical_records cr
            INNER JOIN appointments a ON cr.appointment_id = a.id
            WHERE a.clinic_id = :clinic_id
        """, {"clinic_id": clinic_id}, "clinical_records")
        
        await safe_delete_optional("""
            DELETE pc FROM patient_calls pc
            INNER JOIN appointments a ON pc.appointment_id = a.id
            WHERE a.clinic_id = :clinic_id
        """, {"clinic_id": clinic_id}, "patient_calls")
        
        await safe_delete_optional("""
            DELETE fu FROM file_uploads fu
            INNER JOIN appointments a ON fu.appointment_id = a.id
            WHERE a.clinic_id = :clinic_id
        """, {"clinic_id": clinic_id}, "file_uploads")
        
        await safe_delete_optional("""
            DELETE vs FROM voice_sessions vs
            INNER JOIN appointments a ON vs.appointment_id = a.id
            WHERE a.clinic_id = :clinic_id
        """, {"clinic_id": clinic_id}, "voice_sessions (by appointment)")
        
        # Delete stock movements (optional - table might not exist)
        await safe_delete_optional("DELETE FROM stock_movements WHERE clinic_id = :clinic_id", {"clinic_id": clinic_id}, "stock_movements")
        
        # Delete procedures (optional - table might not exist)
        await safe_delete_optional("DELETE FROM procedures WHERE clinic_id = :clinic_id", {"clinic_id": clinic_id}, "procedures")
        
        # Delete insurance plans (optional - table might not exist)
        await safe_delete_optional("DELETE FROM insurance_plans WHERE clinic_id = :clinic_id", {"clinic_id": clinic_id}, "insurance_plans")
        
        # Delete preauth requests (optional - table might not exist)
        await safe_delete_optional("DELETE FROM preauth_requests WHERE clinic_id = :clinic_id", {"clinic_id": clinic_id}, "preauth_requests")
        
        # Delete stock alerts (optional - table might not exist)
        await safe_delete_optional("DELETE FROM stock_alerts WHERE clinic_id = :clinic_id", {"clinic_id": clinic_id}, "stock_alerts")
        
        # Delete message threads (optional - table might not exist)
        await safe_delete_optional("DELETE FROM message_threads WHERE clinic_id = :clinic_id", {"clinic_id": clinic_id}, "message_threads")
        
        # Delete voice sessions by user_id (optional - table might not exist)
        # Note: voice_sessions by appointment_id were already deleted above
        await safe_delete_optional("""
            DELETE vs FROM voice_sessions vs
            INNER JOIN users u ON vs.user_id = u.id
            WHERE u.clinic_id = :clinic_id
               AND vs.appointment_id IS NULL
        """, {"clinic_id": clinic_id}, "voice_sessions (by user)")
        
        # Delete user settings (optional - table might not exist)
        await safe_delete_optional("""
            DELETE us FROM user_settings us
            INNER JOIN users u ON us.user_id = u.id
            WHERE u.clinic_id = :clinic_id
        """, {"clinic_id": clinic_id}, "user_settings")
        
        # Delete AI configs (optional - table might not exist)
        await safe_delete_optional("DELETE FROM ai_configs WHERE clinic_id = :clinic_id", {"clinic_id": clinic_id}, "ai_configs")
        
        # Delete exam catalogs (optional - table might not exist)
        await safe_delete_optional("DELETE FROM exam_catalog WHERE clinic_id = :clinic_id", {"clinic_id": clinic_id}, "exam_catalog")
        
        # Delete exam requests (optional - table might not exist)
        # Note: exam_requests references clinical_records, not clinic_id directly
        # Using two-step approach: first get clinical_record_ids, then delete
        try:
            logger.info(f"Attempting to delete exam_requests for clinic {clinic_id}")
            # First, get the clinical_record_ids for this clinic
            clinical_records_query = text("""
                SELECT cr.id FROM clinical_records cr
                INNER JOIN appointments a ON cr.appointment_id = a.id
                WHERE a.clinic_id = :clinic_id
            """)
            result = await db.execute(clinical_records_query, {"clinic_id": clinic_id})
            rows = result.fetchall()
            clinical_record_ids = [row[0] for row in rows] if rows else []
            
            if clinical_record_ids:
                # Delete exam_requests for these clinical records using IN clause
                # Build the query with proper parameter binding
                ids_str = ','.join([str(cr_id) for cr_id in clinical_record_ids])
                delete_query = f"DELETE FROM exam_requests WHERE clinical_record_id IN ({ids_str})"
                await db.execute(text(delete_query))
                logger.info(f"Successfully deleted exam_requests for {len(clinical_record_ids)} clinical records")
            else:
                logger.info(f"No clinical records found for clinic {clinic_id}, skipping exam_requests deletion")
        except Exception as e:
            error_msg = str(e).lower()
            logger.warning(f"Error deleting exam_requests: {error_msg}")
            # If table doesn't exist or column doesn't exist, just skip (don't exit function)
            if ("does not exist" in error_msg or "undefinedtable" in error_msg or 
                "table" in error_msg and "doesn't exist" in error_msg or
                "unknown table" in error_msg or "unknown column" in error_msg):
                logger.info(f"exam_requests table or column does not exist, skipping")
                try:
                    await db.rollback()
                    await db.execute(text("SELECT 1"))
                except Exception as rollback_error:
                    logger.warning(f"Error during rollback/restart: {rollback_error}")
                # Continue to next deletion instead of returning
            else:
                # For other errors, re-raise
                await db.rollback()
                raise
        
        # PHASE 2: Delete critical tables (these must succeed)
        # After all optional tables are handled, delete critical tables
        # This ensures that if there was a ROLLBACK from optional tables, we still have a clean transaction
        
        # 1. First, clear appointment_id references in invoices (invoices reference appointments)
        await safe_delete("""
            UPDATE invoices i
            INNER JOIN appointments a ON i.appointment_id = a.id
            SET i.appointment_id = NULL 
            WHERE a.clinic_id = :clinic_id
        """, {"clinic_id": clinic_id}, "invoices.appointment_id")
        
        # 2. Delete invoice_lines (must be deleted before invoices)
        # Handle case where invoices table may not have clinic_id column
        try:
            logger.info(f"Attempting to delete invoice_lines for clinic {clinic_id}")
            # Try method 1: If invoices has clinic_id, use it directly
            try:
                await db.execute(text("""
                    DELETE il FROM invoice_lines il
                    INNER JOIN invoices i ON il.invoice_id = i.id
                    WHERE i.clinic_id = :clinic_id
                """), {"clinic_id": clinic_id})
                logger.info(f"Successfully deleted invoice_lines using invoices.clinic_id")
            except Exception as e1:
                error_msg1 = str(e1).lower()
                if "unknown column" in error_msg1 and "clinic_id" in error_msg1:
                    # Method 1 failed, try method 2: Join through appointments
                    logger.info(f"invoices.clinic_id doesn't exist, trying join through appointments")
                    try:
                        await db.execute(text("""
                            DELETE il FROM invoice_lines il
                            INNER JOIN invoices i ON il.invoice_id = i.id
                            INNER JOIN appointments a ON i.appointment_id = a.id
                            WHERE a.clinic_id = :clinic_id
                        """), {"clinic_id": clinic_id})
                        logger.info(f"Successfully deleted invoice_lines using appointments.clinic_id")
                    except Exception as e2:
                        error_msg2 = str(e2).lower()
                        if "unknown column" in error_msg2 or "null" in error_msg2:
                            # Method 2 failed, try method 3: Join through patients
                            logger.info(f"Join through appointments failed, trying join through patients")
                            await db.execute(text("""
                                DELETE il FROM invoice_lines il
                                INNER JOIN invoices i ON il.invoice_id = i.id
                                INNER JOIN patients pt ON i.patient_id = pt.id
                                WHERE pt.clinic_id = :clinic_id
                            """), {"clinic_id": clinic_id})
                            logger.info(f"Successfully deleted invoice_lines using patients.clinic_id")
                        else:
                            raise
                else:
                    raise
        except Exception as e:
            error_msg = str(e).lower()
            logger.warning(f"Error deleting invoice_lines: {error_msg}")
            # If table doesn't exist or column doesn't exist, just skip (don't exit function)
            if ("does not exist" in error_msg or "undefinedtable" in error_msg or 
                "table" in error_msg and "doesn't exist" in error_msg or
                "unknown table" in error_msg or "unknown column" in error_msg):
                logger.info(f"invoice_lines deletion skipped due to schema mismatch or missing table")
                try:
                    await db.rollback()
                    await db.execute(text("SELECT 1"))
                except Exception as rollback_error:
                    logger.warning(f"Error during rollback/restart: {rollback_error}")
                # Continue to next deletion instead of returning
            else:
                # For other errors, re-raise
                await db.rollback()
                raise
        
        # 3. Delete payments (may reference users and invoices)
        # Must be deleted before invoices to avoid foreign key issues
        # Delete payments linked to invoices from this clinic
        # Note: invoices may not have clinic_id directly, so we join through appointments or patients
        try:
            logger.info(f"Attempting to delete payments linked to invoices for clinic {clinic_id}")
            # Try method 1: If invoices has clinic_id, use it directly
            try:
                await db.execute(text("""
                    DELETE p FROM payments p
                    INNER JOIN invoices i ON p.invoice_id = i.id
                    WHERE i.clinic_id = :clinic_id
                """), {"clinic_id": clinic_id})
                logger.info(f"Successfully deleted payments using invoices.clinic_id")
            except Exception as e1:
                error_msg1 = str(e1).lower()
                if "unknown column" in error_msg1 and "clinic_id" in error_msg1:
                    # Method 1 failed, try method 2: Join through appointments
                    logger.info(f"invoices.clinic_id doesn't exist, trying join through appointments")
                    try:
                        await db.execute(text("""
                            DELETE p FROM payments p
                            INNER JOIN invoices i ON p.invoice_id = i.id
                            INNER JOIN appointments a ON i.appointment_id = a.id
                            WHERE a.clinic_id = :clinic_id
                        """), {"clinic_id": clinic_id})
                        logger.info(f"Successfully deleted payments using appointments.clinic_id")
                    except Exception as e2:
                        error_msg2 = str(e2).lower()
                        if "unknown column" in error_msg2 or "null" in error_msg2:
                            # Method 2 failed, try method 3: Join through patients
                            logger.info(f"Join through appointments failed, trying join through patients")
                            await db.execute(text("""
                                DELETE p FROM payments p
                                INNER JOIN invoices i ON p.invoice_id = i.id
                                INNER JOIN patients pt ON i.patient_id = pt.id
                                WHERE pt.clinic_id = :clinic_id
                            """), {"clinic_id": clinic_id})
                            logger.info(f"Successfully deleted payments using patients.clinic_id")
                        else:
                            raise
                else:
                    raise
        except Exception as e:
            error_msg = str(e).lower()
            logger.warning(f"Error deleting payments by invoice: {error_msg}")
            # If it's an "unknown column" error, just skip (table might have different schema)
            if "unknown column" in error_msg:
                logger.info(f"Payments deletion skipped due to schema mismatch")
                try:
                    await db.rollback()
                    await db.execute(text("SELECT 1"))
                except Exception as rollback_error:
                    logger.warning(f"Error during rollback/restart: {rollback_error}")
            else:
                # For other errors, re-raise
                await db.rollback()
                raise
        
        # Delete payments created by users from this clinic
        await safe_delete("""
            DELETE p FROM payments p
            INNER JOIN users u ON p.created_by = u.id
            WHERE u.clinic_id = :clinic_id
        """, {"clinic_id": clinic_id}, "payments (by user)")
        
        # 4. Delete invoices (must be deleted before appointments since invoices reference appointments)
        # Note: We already cleared appointment_id references above, so this should be safe
        # Handle case where invoices table may not have clinic_id column
        try:
            logger.info(f"Attempting to delete invoices for clinic {clinic_id}")
            # Try method 1: If invoices has clinic_id, use it directly
            try:
                await db.execute(text("DELETE FROM invoices WHERE clinic_id = :clinic_id"), {"clinic_id": clinic_id})
                logger.info(f"Successfully deleted invoices using clinic_id")
            except Exception as e1:
                error_msg1 = str(e1).lower()
                if "unknown column" in error_msg1 and "clinic_id" in error_msg1:
                    # Method 1 failed, try method 2: Join through appointments
                    logger.info(f"invoices.clinic_id doesn't exist, trying join through appointments")
                    try:
                        await db.execute(text("""
                            DELETE i FROM invoices i
                            INNER JOIN appointments a ON i.appointment_id = a.id
                            WHERE a.clinic_id = :clinic_id
                        """), {"clinic_id": clinic_id})
                        logger.info(f"Successfully deleted invoices using appointments.clinic_id")
                    except Exception as e2:
                        error_msg2 = str(e2).lower()
                        if "unknown column" in error_msg2 or "null" in error_msg2:
                            # Method 2 failed, try method 3: Join through patients
                            logger.info(f"Join through appointments failed, trying join through patients")
                            await db.execute(text("""
                                DELETE i FROM invoices i
                                INNER JOIN patients pt ON i.patient_id = pt.id
                                WHERE pt.clinic_id = :clinic_id
                            """), {"clinic_id": clinic_id})
                            logger.info(f"Successfully deleted invoices using patients.clinic_id")
                        else:
                            raise
                else:
                    # For other errors (foreign key, constraint), re-raise
                    if "foreign key" in error_msg1 or "constraint" in error_msg1:
                        await db.rollback()
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Erro ao deletar invoices: {str(e1)}"
                        )
                    raise
        except HTTPException:
            raise
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"Error deleting invoices: {error_msg}")
            if "foreign key" in error_msg or "constraint" in error_msg:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao deletar invoices: {str(e)}"
                )
            raise
        
        # 5. Now we can safely delete appointments (they reference users and patients)
        # All references to appointments have been cleared or deleted
        try:
            logger.info(f"Attempting to delete appointments for clinic {clinic_id}")
            await db.execute(text("DELETE FROM appointments WHERE clinic_id = :clinic_id"), {"clinic_id": clinic_id})
            logger.info(f"Successfully deleted appointments for clinic {clinic_id}")
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"Error deleting appointments: {error_msg}")
            if "foreign key" in error_msg or "constraint" in error_msg:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao deletar appointments: {str(e)}"
                )
            raise
        
        # 6. Delete patients
        await safe_delete("DELETE FROM patients WHERE clinic_id = :clinic_id", {"clinic_id": clinic_id}, "patients")
        
        # 7. Delete users (after appointments and payments that reference them)
        await safe_delete("DELETE FROM users WHERE clinic_id = :clinic_id", {"clinic_id": clinic_id}, "users")
        
        # 8. Delete products
        await safe_delete("DELETE FROM products WHERE clinic_id = :clinic_id", {"clinic_id": clinic_id}, "products")
        
        # 9. Delete service_items (they reference clinics)
        await safe_delete_optional("DELETE FROM service_items WHERE clinic_id = :clinic_id", {"clinic_id": clinic_id}, "service_items")
        
        # Check for any remaining references to the clinic (e.g., licenses)
        # Delete license relationship if exists
        await safe_delete_optional("""
            UPDATE clinics 
            SET license_id = NULL 
            WHERE id = :clinic_id
        """, {"clinic_id": clinic_id}, "clinics.license_id")
        
        # Finally, delete the clinic itself
        try:
            logger.info(f"Attempting to delete clinic {clinic_id} (name: {clinic_name})")
            await db.execute(text("DELETE FROM clinics WHERE id = :clinic_id"), {"clinic_id": clinic_id})
            await db.commit()
            logger.info(f"Successfully deleted clinic {clinic_id} (name: {clinic_name})")
            
            # Log the deletion (optional - table might not exist)
            try:
                system_log = SystemLog(
                    level="info",
                    source="admin",
                    message=f"Clinic '{clinic_name}' (ID: {clinic_id_for_log}) was deleted by {deleted_by}",
                    metadata={"clinic_id": clinic_id_for_log, "clinic_name": clinic_name, "deleted_by": deleted_by}
                )
                db.add(system_log)
                await db.commit()
            except Exception as log_error:
                error_msg = str(log_error).lower()
                logger.warning(f"Failed to create system log for clinic deletion: {log_error}")
                # If table doesn't exist, rollback and restart transaction to clear session state
                if "does not exist" in error_msg or "table" in error_msg and "doesn't exist" in error_msg:
                    try:
                        await db.rollback()
                        # Restart transaction by executing a simple query
                        await db.execute(text("SELECT 1"))
                    except Exception as rollback_error:
                        logger.warning(f"Error during rollback/restart after system log failure: {rollback_error}")
                # For other errors, also rollback to clear session state
                else:
                    try:
                        await db.rollback()
                        await db.execute(text("SELECT 1"))
                    except Exception as rollback_error:
                        logger.warning(f"Error during rollback/restart after system log failure: {rollback_error}")
        except Exception as delete_error:
            await db.rollback()
            error_msg = str(delete_error)
            # Log the full error for debugging
            logger.error(f"Failed to delete clinic {clinic_id}: {error_msg}", exc_info=True)
            
            # Check for foreign key constraint errors
            if "foreign key" in error_msg.lower() or "constraint" in error_msg.lower() or "violates foreign key" in error_msg.lower():
                # Try to extract the table name from the error message
                table_name = None
                table_display_name = None
                
                # Common table mappings for better user messages
                table_mappings = {
                    "licenses": "licenças",
                    "users": "usuários",
                    "patients": "pacientes",
                    "appointments": "agendamentos",
                    "invoices": "faturas",
                    "products": "produtos",
                    "stock_movements": "movimentações de estoque",
                    "procedures": "procedimentos",
                    "messages": "mensagens",
                    "message_threads": "conversas",
                }
                
                # Extract table name from error message
                error_lower = error_msg.lower()
                for table, display_name in table_mappings.items():
                    # Check for various patterns in the error message
                    if (f'"{table}"' in error_lower or 
                        f"table \"{table}\"" in error_lower or 
                        f"on table \"{table}\"" in error_lower or
                        f"from table \"{table}\"" in error_lower or
                        f"references table \"{table}\"" in error_lower or
                        f"constraint \"{table}" in error_lower):
                        table_name = table
                        table_display_name = display_name
                        break
                
                # If we found a specific table, provide a more helpful message
                if table_name and table_display_name:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Não é possível excluir esta clínica porque existem {table_display_name} associadas a ela. Para excluir a clínica, você precisa primeiro remover ou transferir todas as {table_display_name} relacionadas. Acesse a seção de {table_display_name} e remova os registros antes de tentar excluir a clínica novamente."
                    )
                else:
                    # Generic message if we can't identify the table
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Não é possível excluir esta clínica porque existem registros relacionados que impedem a exclusão. Para excluir a clínica, você precisa primeiro remover ou transferir todos os registros relacionados (licenças, usuários, pacientes, agendamentos, etc.). Acesse cada seção do sistema e remova os registros antes de tentar excluir a clínica novamente."
                    )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao excluir clínica. Por favor, tente novamente. Se o problema persistir, entre em contato com o suporte."
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        await db.rollback()
        error_msg = str(e)
        # Log the full error for debugging
        logger.error(f"Unexpected error deleting clinic {clinic_id}: {error_msg}", exc_info=True)
        
        # Check for foreign key constraint errors
        if "foreign key" in error_msg.lower() or "constraint" in error_msg.lower() or "violates foreign key" in error_msg.lower():
            # Try to extract the table name from the error message
            table_name = None
            table_display_name = None
            
            # Common table mappings for better user messages
            table_mappings = {
                "licenses": "licenças",
                "users": "usuários",
                "patients": "pacientes",
                "appointments": "agendamentos",
                "invoices": "faturas",
                "products": "produtos",
                "stock_movements": "movimentações de estoque",
                "procedures": "procedimentos",
                "messages": "mensagens",
                "message_threads": "conversas",
            }
            
            # Extract table name from error message
            error_lower = error_msg.lower()
            for table, display_name in table_mappings.items():
                # Check for various patterns in the error message
                if (f'"{table}"' in error_lower or 
                    f"table \"{table}\"" in error_lower or 
                    f"on table \"{table}\"" in error_lower or
                    f"from table \"{table}\"" in error_lower or
                    f"references table \"{table}\"" in error_lower or
                    f"constraint \"{table}" in error_lower):
                    table_name = table
                    table_display_name = display_name
                    break
            
            # If we found a specific table, provide a more helpful message
            if table_name and table_display_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Não é possível excluir esta clínica porque existem {table_display_name} associadas a ela. Para excluir a clínica, você precisa primeiro remover ou transferir todas as {table_display_name} relacionadas. Acesse a seção de {table_display_name} e remova os registros antes de tentar excluir a clínica novamente."
                )
            else:
                # Generic message if we can't identify the table
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Não é possível excluir esta clínica porque existem registros relacionados que impedem a exclusão. Para excluir a clínica, você precisa primeiro remover ou transferir todos os registros relacionados (licenças, usuários, pacientes, agendamentos, etc.). Acesse cada seção do sistema e remova os registros antes de tentar excluir a clínica novamente."
                )
        # Check for missing table errors
        if ("does not exist" in error_msg.lower() or "undefinedtable" in error_msg.lower() or 
            "unknown table" in error_msg.lower() or "table" in error_msg.lower() and "doesn't exist" in error_msg.lower()):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao excluir clínica: Tabela não encontrada no banco de dados. Erro: {error_msg}. Por favor, verifique as migrações do banco de dados ou entre em contato com o suporte técnico."
            )
        # Check for MySQL-specific errors
        if "cannot delete" in error_msg.lower() or "cannot update" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível excluir esta clínica devido a restrições no banco de dados. Erro: {error_msg}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir clínica: {error_msg}. Por favor, tente novamente. Se o problema persistir, entre em contato com o suporte."
        )
    
    return {"message": "Clinic deleted successfully"}


# ==================== System Logs ====================

@router.get("/logs", response_model=List[SystemLogResponse])
async def list_logs(
    level: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        query = select(SystemLog)
        if level:
            query = query.filter(SystemLog.level == level)
        if source:
            query = query.filter(SystemLog.source == source)
        if search:
            like = f"%{search}%"
            query = query.filter(or_(SystemLog.message.ilike(like), SystemLog.details.ilike(like)))
        query = query.order_by(SystemLog.timestamp.desc()).limit(limit)
        result = await db.execute(query)
        logs = result.scalars().all()
        return [SystemLogResponse.model_validate(l) for l in logs]
    except SQLAlchemyError as e:
        # If table doesn't exist yet, return empty list gracefully
        if "relation \"system_logs\" does not exist" in str(e):
            return []
        raise


@router.post("/logs", response_model=SystemLogResponse, status_code=status.HTTP_201_CREATED)
async def create_log(
    payload: SystemLogCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session),
):
    log = SystemLog(
        level=payload.level,
        message=payload.message,
        source=payload.source,
        details=payload.details,
        user_id=payload.user_id or current_user.id,
        clinic_id=payload.clinic_id or current_user.clinic_id,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return SystemLogResponse.model_validate(log)


@router.put("/logs/{log_id}", response_model=SystemLogResponse)
async def update_log(
    log_id: int,
    payload: SystemLogUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(select(SystemLog).where(SystemLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(log, k, v)
    await db.commit()
    await db.refresh(log)
    return SystemLogResponse.model_validate(log)


@router.delete("/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_log(
    log_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(select(SystemLog).where(SystemLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    await db.delete(log)
    await db.commit()
    return {"status": "ok"}


@router.get("/modules", response_model=List[str])
async def get_available_modules(
    current_user: User = Depends(require_admin)
):
    """
    Get list of available modules
    """
    return AVAILABLE_MODULES


@router.patch("/clinics/me/modules", response_model=ClinicResponse)
async def update_my_clinic_modules(
    modules_data: Dict[str, Any],
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update the current clinic's active modules
    Only admins can update modules
    """
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not associated with a clinic"
        )
    
    query = select(Clinic).filter(Clinic.id == current_user.clinic_id)
    result = await db.execute(query)
    clinic = result.scalar_one_or_none()
    
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    
    # Validate modules
    active_modules = modules_data.get("active_modules", [])
    if not isinstance(active_modules, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="active_modules must be a list"
        )
    
    # Validate each module
    for module in active_modules:
        if module not in AVAILABLE_MODULES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid module: {module}. Available modules: {AVAILABLE_MODULES}"
            )
    
    # Update modules
    clinic.active_modules = active_modules
    await db.commit()
    await db.refresh(clinic)
    
    # Return updated clinic - use same conversion approach
    from datetime import date as date_type, datetime
    
    def to_date(dt_value):
        """Convert datetime or date to pure date object - guaranteed"""
        if dt_value is None:
            return None
        if isinstance(dt_value, date_type):
            return date_type(dt_value.year, dt_value.month, dt_value.day)
        if isinstance(dt_value, datetime):
            if dt_value.tzinfo is not None:
                from datetime import timezone as tz
                dt_value = dt_value.astimezone(tz.utc)
            return date_type(dt_value.year, dt_value.month, dt_value.day)
        if hasattr(dt_value, 'date'):
            dt_result = dt_value.date()
            if isinstance(dt_result, datetime):
                if dt_result.tzinfo is not None:
                    from datetime import timezone as tz
                    dt_result = dt_result.astimezone(tz.utc)
                return date_type(dt_result.year, dt_result.month, dt_result.day)
            if isinstance(dt_result, date_type):
                return date_type(dt_result.year, dt_result.month, dt_result.day)
        return date_type.today()
    
    response_dict = {
        "id": clinic.id,
        "name": clinic.name,
        "legal_name": clinic.legal_name,
        "tax_id": clinic.tax_id,
        "address": clinic.address,
        "phone": clinic.phone,
        "email": clinic.email,
        "is_active": clinic.is_active,
        "license_key": clinic.license_key,
        "expiration_date": clinic.expiration_date,
        "max_users": clinic.max_users,
        "active_modules": clinic.active_modules or [],
        "created_at": to_date(getattr(clinic, "created_at", None)) or date_type.today(),
        "updated_at": to_date(getattr(clinic, "updated_at", None)),
    }
    
    try:
        return ClinicResponse.model_validate(response_dict)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"ClinicResponse validation failed: {e}")
        return ClinicResponse.model_construct(**response_dict)


@router.patch("/clinics/{clinic_id}/modules", response_model=ClinicResponse)
async def update_clinic_modules(
    clinic_id: int,
    modules_data: dict,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update clinic active modules
    """
    clinic = await db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    
    # Validate modules
    available_modules = [
        "patients", "appointments", "clinical", "financial", 
        "stock", "bi", "procedures", "tiss", "mobile", "telemed"
    ]
    
    active_modules = modules_data.get("active_modules", [])
    if not isinstance(active_modules, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="active_modules must be a list"
        )
    
    # Validate each module
    for module in active_modules:
        if module not in available_modules:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid module: {module}. Available modules: {available_modules}"
            )
    
    # Update modules
    clinic.active_modules = active_modules
    await db.commit()
    await db.refresh(clinic)
    
    return clinic


@router.get("/database/test-connections")
async def test_database_connections(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Test database connections for each module by attempting to query their tables
    Returns status for each module: success, error message, and response time
    """
    results: Dict[str, Dict[str, Any]] = {}
    
    # Define modules and their test queries
    module_tests = {
        "patients": {
            "table": Patient,
            "query": select(func.count(Patient.id))
        },
        "appointments": {
            "table": Appointment,
            "query": select(func.count(Appointment.id))
        },
        "clinical": {
            "table": ClinicalRecord,
            "query": select(func.count(ClinicalRecord.id))
        },
        "prescriptions": {
            "table": Prescription,
            "query": select(func.count(Prescription.id))
        },
        "diagnoses": {
            "table": Diagnosis,
            "query": select(func.count(Diagnosis.id))
        },
        "financial": {
            "table": Invoice,
            "query": select(func.count(Invoice.id))
        },
        "payments": {
            "table": Payment,
            "query": select(func.count(Payment.id))
        },
        "service_items": {
            "table": ServiceItem,
            "query": select(func.count(ServiceItem.id))
        },
        "stock": {
            "table": Product,
            "query": select(func.count(Product.id))
        },
        "stock_movements": {
            "table": StockMovement,
            "query": select(func.count(StockMovement.id))
        },
        "procedures": {
            "table": Procedure,
            "query": select(func.count(Procedure.id))
        },
        "users": {
            "table": User,
            "query": select(func.count(User.id))
        },
        "clinics": {
            "table": Clinic,
            "query": select(func.count(Clinic.id))
        }
    }
    
    # Test each module
    for module_name, test_config in module_tests.items():
        start_time = asyncio.get_event_loop().time()
        try:
            result = await db.execute(test_config["query"])
            count = result.scalar()
            end_time = asyncio.get_event_loop().time()
            response_time_ms = round((end_time - start_time) * 1000, 2)
            
            results[module_name] = {
                "status": "success",
                "message": f"Connection successful",
                "record_count": count,
                "response_time_ms": response_time_ms,
                "error": None
            }
        except SQLAlchemyError as e:
            end_time = asyncio.get_event_loop().time()
            response_time_ms = round((end_time - start_time) * 1000, 2)
            
            results[module_name] = {
                "status": "error",
                "message": f"Database error: {str(e)}",
                "record_count": None,
                "response_time_ms": response_time_ms,
                "error": str(e)
            }
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            response_time_ms = round((end_time - start_time) * 1000, 2)
            
            results[module_name] = {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "record_count": None,
                "response_time_ms": response_time_ms,
                "error": str(e)
            }
    
    # Calculate summary
    total_modules = len(results)
    successful_modules = sum(1 for r in results.values() if r["status"] == "success")
    failed_modules = total_modules - successful_modules
    avg_response_time = sum(r["response_time_ms"] for r in results.values()) / total_modules if total_modules > 0 else 0
    
    return {
        "summary": {
            "total_modules": total_modules,
            "successful": successful_modules,
            "failed": failed_modules,
            "average_response_time_ms": round(avg_response_time, 2)
        },
        "modules": results
    }
