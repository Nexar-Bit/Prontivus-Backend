from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_async_session
from app.core.auth import get_current_user
from app.models import User
from app.models.migration import MigrationJob, MigrationStatus
from app.schemas.migration import MigrationJobCreate, MigrationJobResponse
from app.services.migration_service import create_job, run_job
from app.services.migration_reports import pre_migration_quality, post_migration_validation

router = APIRouter(prefix="/migration", tags=["Migration"])


@router.post("/jobs", response_model=MigrationJobResponse)
async def create_migration_job(payload: MigrationJobCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    job = await create_job(db, current_user.clinic_id, current_user.id, payload.type, payload.input_format, payload.source_name, payload.params)
    await db.commit()
    return job


@router.post("/jobs/{job_id}/upload", response_model=MigrationJobResponse)
async def upload_migration_data(job_id: int, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    res = await db.execute(select(MigrationJob).where(MigrationJob.id == job_id, MigrationJob.clinic_id == current_user.clinic_id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    content = await file.read()
    try:
        # Pre-quality (best-effort)
        try:
            import json
            pre_records = []
            if job.input_format == 'json':
                pre_records = json.loads(content.decode('utf-8'))
                if isinstance(pre_records, dict):
                    pre_records = [pre_records]
            pre = pre_migration_quality(pre_records) if pre_records else None
        except Exception:
            pre = None

        imported, stats, errors = await run_job(db, job, content)
        # Post validation
        post = post_migration_validation(imported, stats)
        # Attach report
        job.stats = {**(job.stats or {}), 'pre_quality': pre, 'post_validation': post}
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return job


@router.get("/jobs", response_model=list[MigrationJobResponse])
async def list_jobs(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    try:
        if not current_user.clinic_id:
            raise HTTPException(status_code=400, detail="User must be associated with a clinic")
        
        res = await db.execute(select(MigrationJob).where(MigrationJob.clinic_id == current_user.clinic_id).order_by(MigrationJob.created_at.desc()))
        jobs = res.scalars().all()
        return jobs
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error listing migration jobs: {str(e)}")


@router.post("/jobs/{job_id}/rollback", response_model=MigrationJobResponse)
async def rollback_job(job_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    res = await db.execute(select(MigrationJob).where(MigrationJob.id == job_id, MigrationJob.clinic_id == current_user.clinic_id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Implement domain-specific rollback based on migration type
    # This would reverse the changes made during the migration
    if job.type == MigrationType.PATIENTS:
        # For patient migrations, you would:
        # 1. Delete imported patient records
        # 2. Restore original data if backed up
        # 3. Clean up related records (appointments, clinical records, etc.)
        logger.info(f"Rolling back patient migration job {job_id}")
        # Implementation would go here - for now, just mark as rolled back
    elif job.type == MigrationType.APPOINTMENTS:
        # For appointment migrations, delete imported appointments
        logger.info(f"Rolling back appointment migration job {job_id}")
        # Implementation would go here
    elif job.type == MigrationType.FINANCIAL:
        # For financial migrations, reverse transactions
        logger.info(f"Rolling back financial migration job {job_id}")
        # Implementation would go here
    
    job.status = MigrationStatus.ROLLED_BACK
    await db.commit()
    logger.info(f"Migration job {job_id} marked as rolled back")
    return job


