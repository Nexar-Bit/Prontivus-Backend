"""
S3 Reports API
Manage PDF reports with AWS S3 storage
Supports: View, Download, Upload to S3
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging
from io import BytesIO

from app.models import User
from app.core.auth import get_current_user
from app.services.s3_service import s3_service
from database import get_async_session

router = APIRouter(prefix="/s3-reports", tags=["S3 Reports"])
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_report_to_s3(
    report_type: str = Query(..., description="Type of report: billing, sales, doctor_billing, stock, payable, receivable"),
    report_id: Optional[int] = Query(None, description="Optional report ID"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Upload PDF report to S3
    
    Report types:
    - billing: Relatório de Faturamento
    - sales: Relatório de Vendas
    - doctor_billing: Relatório de Faturamento por médico
    - stock: Relatório de Estoque (Movimentação)
    - payable: Contas a pagar
    - receivable: Contas a receber
    """
    if not s3_service.is_enabled():
        raise HTTPException(
            status_code=503,
            detail="AWS S3 is not configured. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_S3_BUCKET_NAME"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Validate PDF
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        if len(file_content) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File too large. Maximum size: 50MB")
        
        # Upload to S3
        result = await s3_service.upload_report(
            file_content=file_content,
            clinic_id=current_user.clinic_id,
            report_type=report_type,
            report_id=report_id,
            filename=file.filename,
            metadata={
                "uploaded_by": str(current_user.id),
                "original_filename": file.filename
            }
        )
        
        return {
            "success": True,
            "message": "Report uploaded successfully",
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{report_type}/{year}/{month}/{filename}")
async def download_report_from_s3(
    report_type: str,
    year: str,
    month: str,
    filename: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Download PDF report from S3"""
    if not s3_service.is_enabled():
        raise HTTPException(status_code=503, detail="AWS S3 is not configured")
    
    try:
        # Construct S3 key
        key = f"clinics/{current_user.clinic_id}/reports/{report_type}/{year}/{month}/{filename}"
        
        # Download from S3
        file_content = await s3_service.download_report(key)
        
        # Return as streaming response
        return StreamingResponse(
            BytesIO(file_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/view/{report_type}/{year}/{month}/{filename}")
async def view_report_from_s3(
    report_type: str,
    year: str,
    month: str,
    filename: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """View PDF report from S3 (inline in browser)"""
    if not s3_service.is_enabled():
        raise HTTPException(status_code=503, detail="AWS S3 is not configured")
    
    try:
        # Construct S3 key
        key = f"clinics/{current_user.clinic_id}/reports/{report_type}/{year}/{month}/{filename}"
        
        # Download from S3
        file_content = await s3_service.download_report(key)
        
        # Return for inline viewing
        return Response(
            content=file_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"'
            }
        )
        
    except Exception as e:
        logger.error(f"Error viewing report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presigned-url")
async def get_presigned_download_url(
    key: str = Query(..., description="S3 object key"),
    expiration: int = Query(3600, description="URL expiration in seconds"),
    download: bool = Query(True, description="Force download vs inline view"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Generate presigned URL for temporary access to report
    
    Useful for:
    - Sharing reports via email
    - Temporary access links
    - Mobile app downloads
    """
    if not s3_service.is_enabled():
        raise HTTPException(status_code=503, detail="AWS S3 is not configured")
    
    try:
        # Verify key belongs to user's clinic
        if not key.startswith(f"clinics/{current_user.clinic_id}/"):
            raise HTTPException(status_code=403, detail="Unauthorized access to report")
        
        # Generate presigned URL
        url = await s3_service.generate_presigned_url(
            key=key,
            expiration=expiration,
            download=download
        )
        
        return {
            "success": True,
            "url": url,
            "expires_in": expiration,
            "key": key
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """List all reports for current clinic"""
    if not s3_service.is_enabled():
        raise HTTPException(status_code=503, detail="AWS S3 is not configured")
    
    try:
        reports = await s3_service.list_reports(
            clinic_id=current_user.clinic_id,
            report_type=report_type
        )
        
        return {
            "success": True,
            "count": len(reports),
            "reports": reports
        }
        
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata")
async def get_report_metadata(
    key: str = Query(..., description="S3 object key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get report metadata from S3"""
    if not s3_service.is_enabled():
        raise HTTPException(status_code=503, detail="AWS S3 is not configured")
    
    try:
        # Verify key belongs to user's clinic
        if not key.startswith(f"clinics/{current_user.clinic_id}/"):
            raise HTTPException(status_code=403, detail="Unauthorized access to report")
        
        metadata = await s3_service.get_report_metadata(key)
        
        return {
            "success": True,
            **metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metadata: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete")
async def delete_report(
    key: str = Query(..., description="S3 object key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Delete report from S3"""
    if not s3_service.is_enabled():
        raise HTTPException(status_code=503, detail="AWS S3 is not configured")
    
    try:
        # Verify key belongs to user's clinic
        if not key.startswith(f"clinics/{current_user.clinic_id}/"):
            raise HTTPException(status_code=403, detail="Unauthorized access to report")
        
        # Delete from S3
        await s3_service.delete_report(key)
        
        return {
            "success": True,
            "message": "Report deleted successfully",
            "key": key
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
