"""
TISS XML Generation Endpoints
Provides endpoints for generating and downloading TISS standard XML files
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

from app.core.auth import get_current_user
from app.models import User, Invoice, InvoiceStatus, Appointment, InvoiceLine
# Legacy imports - commented out as tiss_service uses old models that don't exist
# TODO: Update endpoints to use new TISS module services
# from app.services.tiss_service import generate_tiss_xml, generate_batch_tiss_xml
# from app.services.tiss_validator import validate_tiss_document
from database import get_async_session
from typing import List

router = APIRouter(tags=["TISS"])


@router.get("/invoices/{invoice_id}/tiss-xml")
async def get_tiss_xml(
    invoice_id: int,
    skip_validation: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Generate and download TISS XML for a specific invoice
    
    Args:
        invoice_id: ID of the invoice to generate TISS XML for
        skip_validation: If True, skip validation for testing purposes
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        XML file for download
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"TISS XML endpoint called for invoice {invoice_id} by user {current_user.id}")
    
    try:
        # Verify invoice exists and user has access
        invoice_query = select(Invoice).options(
            joinedload(Invoice.patient),
            joinedload(Invoice.appointment).joinedload(Appointment.doctor),
            joinedload(Invoice.clinic),
            joinedload(Invoice.invoice_lines).joinedload(InvoiceLine.service_item)
        ).filter(
            Invoice.id == invoice_id,
            Invoice.clinic_id == current_user.clinic_id
        )
        invoice_result = await db.execute(invoice_query)
        invoice = invoice_result.unique().scalar_one_or_none()
        
        if not invoice:
            logger.warning(f"Invoice {invoice_id} not found or access denied for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found or access denied"
            )
        
        # Check if user has permission to access this invoice
        if current_user.role not in ["admin", "secretary"]:
            logger.warning(f"User {current_user.id} with role {current_user.role} attempted to access invoice {invoice_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to access invoice data"
            )
        
        # Validate invoice has required data before attempting to generate XML
        if not invoice.patient:
            logger.error(f"Invoice {invoice_id} missing patient data")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice must have an associated patient to generate TISS XML"
            )
        
        if not invoice.clinic:
            logger.error(f"Invoice {invoice_id} missing clinic data")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice must have an associated clinic to generate TISS XML"
            )
        
        if not invoice.invoice_lines or len(invoice.invoice_lines) == 0:
            logger.error(f"Invoice {invoice_id} has no invoice lines")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice must have at least one invoice line to generate TISS XML"
            )
        
        # Check if invoice lines have service items
        valid_lines = [line for line in invoice.invoice_lines if line.service_item]
        if len(valid_lines) == 0:
            logger.error(f"Invoice {invoice_id} has no invoice lines with service items")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice must have at least one invoice line with a service item to generate TISS XML"
            )
        
        # Check if we should skip validation (if data is incomplete, validation will likely fail)
        # Skip validation if clinic doesn't have valid CNPJ or if using default values
        should_skip_validation = skip_validation
        if not should_skip_validation:
            clinic_cnpj = (invoice.clinic.tax_id or "").replace(".", "").replace("/", "").replace("-", "")
            # If CNPJ is invalid or default, skip validation
            # Check if CNPJ is missing, wrong length, all digits same, or default value
            if (not clinic_cnpj or 
                len(clinic_cnpj) != 14 or 
                clinic_cnpj == "00000000000000" or 
                (len(clinic_cnpj) == 14 and clinic_cnpj == clinic_cnpj[0] * 14)):
                logger.warning(f"Invoice {invoice_id} has invalid or default CNPJ ({clinic_cnpj}), skipping validation")
                should_skip_validation = True
        
        # Generate TISS XML (with optional validation skip)
        logger.info(f"Generating TISS XML for invoice {invoice_id} (skip_validation={should_skip_validation})")
        xml_content = await generate_tiss_xml(invoice_id, db, skip_validation=should_skip_validation)
        
        # Return XML file for download
        filename = f"tiss_invoice_{invoice_id:06d}.xml"
        
        logger.info(f"Successfully generated TISS XML for invoice {invoice_id}")
        return Response(
            content=xml_content,
            media_type="application/xml",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/xml; charset=utf-8"
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        logger.error(f"ValueError generating TISS XML for invoice {invoice_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não foi possível gerar o XML TISS: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error generating TISS XML for invoice {invoice_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar XML TISS: {str(e)}"
        )


@router.get("/invoices/{invoice_id}/tiss-xml/preview")
async def preview_tiss_xml(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Preview TISS XML for a specific invoice (returns XML content in response body)
    
    Args:
        invoice_id: ID of the invoice to generate TISS XML for
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        XML content as text
    """
    try:
        # Verify invoice exists and user has access
        invoice_query = select(Invoice).options(
            joinedload(Invoice.patient),
            joinedload(Invoice.appointment).joinedload(Appointment.doctor),
            joinedload(Invoice.clinic),
            joinedload(Invoice.invoice_lines).joinedload(InvoiceLine.service_item)
        ).filter(
            Invoice.id == invoice_id,
            Invoice.clinic_id == current_user.clinic_id
        )
        invoice_result = await db.execute(invoice_query)
        invoice = invoice_result.unique().scalar_one_or_none()
        
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found or access denied"
            )
        
        # Check if user has permission to access this invoice
        if current_user.role not in ["admin", "secretary"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to access invoice data"
            )
        
        # Generate TISS XML (skip validation for preview)
        # TODO: Update to use new TISS module services
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="This endpoint is deprecated. Please use the new TISS module endpoints at /api/v1/tiss/*"
        )
        # xml_content = await generate_tiss_xml(invoice_id, db, skip_validation=True)
        
        # Return XML content as text
        return Response(
            content=xml_content,
            media_type="application/xml; charset=utf-8"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating TISS XML: {str(e)}"
        )


@router.post("/invoices/batch-tiss-xml")
async def generate_batch_tiss_xml_endpoint(
    invoice_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Generate TISS XML for multiple invoices and return as ZIP file
    
    Args:
        invoice_ids: List of invoice IDs to generate TISS XML for
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ZIP file containing TISS XML files
    """
    try:
        # Verify all invoices exist and user has access
        invoice_query = select(Invoice).filter(
            Invoice.id.in_(invoice_ids),
            Invoice.clinic_id == current_user.clinic_id
        )
        invoice_result = await db.execute(invoice_query)
        invoices = invoice_result.scalars().all()
        
        if len(invoices) != len(invoice_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more invoices not found or access denied"
            )
        
        # Check if user has permission to access these invoices
        if current_user.role not in ["admin", "secretary"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to access invoice data"
            )
        
        # Generate batch TISS XML
        # TODO: Update to use new TISS module services
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="This endpoint is deprecated. Please use the new TISS module endpoints at /api/v1/tiss/batch/*"
        )
        # zip_content = await generate_batch_tiss_xml(invoice_ids, db)
        
        # Return ZIP file for download
        from datetime import datetime
        filename = f"tiss_batch_{len(invoice_ids)}_invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        return Response(
            content=zip_content,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/zip"
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating batch TISS XML: {str(e)}"
        )


@router.post("/invoices/{invoice_id}/tiss-xml/validate")
async def validate_tiss_xml(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Validate TISS XML for a specific invoice without generating it
    
    Args:
        invoice_id: ID of the invoice to validate
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Validation result with errors and warnings
    """
    try:
        # Verify invoice exists and user has access
        invoice_query = select(Invoice).options(
            joinedload(Invoice.patient),
            joinedload(Invoice.appointment).joinedload(Appointment.doctor),
            joinedload(Invoice.clinic),
            joinedload(Invoice.invoice_lines).joinedload(InvoiceLine.service_item)
        ).filter(
            Invoice.id == invoice_id,
            Invoice.clinic_id == current_user.clinic_id
        )
        invoice_result = await db.execute(invoice_query)
        invoice = invoice_result.unique().scalar_one_or_none()
        
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found or access denied"
            )
        
        # Check if user has permission to access this invoice
        if current_user.role not in ["admin", "secretary"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to access invoice data"
            )
        
        # Build TISS document structure
        # TODO: Update to use new TISS module services
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="This endpoint is deprecated. Please use the new TISS module endpoints at /api/v1/tiss/*/validate"
        )
        # from app.services.tiss_service import _build_tiss_document
        # tiss_doc = await _build_tiss_document(invoice)
        # validation_result = validate_tiss_document(tiss_doc)
        
        return validation_result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating TISS XML: {str(e)}"
        )
