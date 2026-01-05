"""
TISS Submission Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Dict

from database import get_async_session
from app.models import User
from app.core.auth import get_current_user, RoleChecker, UserRole
from app.models.tiss.batch import TISSBatch
from app.services.tiss.submission import SOAPSender, RESTSender, SFTPSender
from app.services.tiss.submission.retry_manager import RetryManager

router = APIRouter(prefix="/tiss/submission", tags=["TISS Submission"])

require_doctor = RoleChecker([UserRole.DOCTOR, UserRole.ADMIN])


class SubmissionRequest(BaseModel):
    method: str  # 'soap', 'rest', 'sftp', 'manual'
    operator_config: Dict  # Operator-specific configuration


@router.post("/{batch_id}/submit")
async def submit_batch(
    batch_id: int,
    submission_data: SubmissionRequest,
    current_user: User = Depends(require_doctor),
    db: AsyncSession = Depends(get_async_session)
):
    """Submit a batch to operator"""
    from sqlalchemy import select
    
    query = select(TISSBatch).where(
        TISSBatch.id == batch_id,
        TISSBatch.clinic_id == current_user.clinic_id
    )
    result = await db.execute(query)
    batch = result.scalar_one_or_none()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    if not batch.xml_content:
        raise HTTPException(status_code=400, detail="Batch XML not generated")
    
    method = submission_data.method.lower()
    operator_config = submission_data.operator_config
    
    # Select sender based on method
    if method == 'soap':
        sender = SOAPSender(
            wsdl_url=operator_config.get('wsdl_url', ''),
            timeout=operator_config.get('timeout', 30)
        )
        result = await sender.send_batch(batch, operator_config)
    elif method == 'rest':
        sender = RESTSender(timeout=operator_config.get('timeout', 30))
        result = await sender.send_batch(batch, operator_config)
    elif method == 'sftp':
        sender = SFTPSender(timeout=operator_config.get('timeout', 30))
        result = await sender.send_batch(batch, operator_config)
    elif method == 'manual':
        # Manual upload - just mark as ready
        result = {
            "success": True,
            "protocol_number": None,
            "message": "Batch ready for manual upload"
        }
    else:
        raise HTTPException(status_code=400, detail=f"Invalid submission method: {method}")
    
    # Update batch status
    if result["success"]:
        batch.submission_status = 'submitted'
        batch.submission_method = method
        batch.protocol_number = result.get("protocol_number")
        batch.error_message = None
    else:
        batch.submission_status = 'error'
        batch.error_message = result.get("error")
    
    await db.commit()
    
    return result

