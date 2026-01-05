"""
Document Signature API Endpoints
Handles digital signature operations for medical documents using AR CFM
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_async_session
from app.core.auth import get_current_user, RoleChecker
from app.models import User, UserRole
from app.models.document_signature import DocumentSignature, SignatureStatus, DocumentType
from app.schemas.document_signature import (
    DocumentSignatureCreate,
    DocumentSignatureResponse,
    DocumentSignatureVerifyRequest,
    DocumentSignatureVerifyResponse,
    DocumentSignatureRevokeRequest
)
from app.services.digital_signature import DigitalSignatureService

router = APIRouter(prefix="/document-signatures", tags=["Document Signatures"])

# Role checkers
require_doctor = RoleChecker([UserRole.DOCTOR, UserRole.ADMIN])


@router.post("", response_model=DocumentSignatureResponse, status_code=status.HTTP_201_CREATED)
async def create_signature(
    signature_data: DocumentSignatureCreate,
    request: Request,
    current_user: User = Depends(require_doctor),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a digital signature for a document
    
    Requires:
    - Doctor role
    - Valid AR CFM certificate information
    - Document hash and signature data
    """
    try:
        # Get IP address and user agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", None)
        
        # Verify document hash matches (optional additional validation)
        # In production, you might want to regenerate the hash from the document
        # and compare it with the provided hash
        
        # Create signature record
        signature = DocumentSignature(
            document_type=signature_data.document_type,
            document_id=signature_data.document_id,
            doctor_id=current_user.id,
            clinic_id=current_user.clinic_id,
            crm_number=signature_data.crm_number,
            crm_state=signature_data.crm_state,
            certificate_serial=signature_data.certificate_serial,
            certificate_issuer=signature_data.certificate_issuer,
            certificate_valid_from=signature_data.certificate_valid_from,
            certificate_valid_to=signature_data.certificate_valid_to,
            document_hash=signature_data.document_hash,
            signature_data=signature_data.signature_data,
            signature_algorithm=signature_data.signature_algorithm,
            status=SignatureStatus.SIGNED,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(signature)
        await db.flush()
        
        # Load doctor relationship for response
        await db.refresh(signature, ["doctor"])
        
        await db.commit()
        
        # Build response
        response = DocumentSignatureResponse(
            id=signature.id,
            document_type=signature.document_type,
            document_id=signature.document_id,
            doctor_id=signature.doctor_id,
            clinic_id=signature.clinic_id,
            crm_number=signature.crm_number,
            crm_state=signature.crm_state,
            certificate_serial=signature.certificate_serial,
            certificate_issuer=signature.certificate_issuer,
            certificate_valid_from=signature.certificate_valid_from,
            certificate_valid_to=signature.certificate_valid_to,
            document_hash=signature.document_hash,
            signature_algorithm=signature.signature_algorithm,
            status=signature.status,
            signed_at=signature.signed_at,
            revoked_at=signature.revoked_at,
            revocation_reason=signature.revocation_reason,
            created_at=signature.created_at,
            updated_at=signature.updated_at,
            doctor_name=f"{signature.doctor.first_name or ''} {signature.doctor.last_name or ''}".strip() if signature.doctor else None
        )
        
        return response
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating signature: {str(e)}"
        )


@router.get("/{signature_id}", response_model=DocumentSignatureResponse)
async def get_signature(
    signature_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get signature by ID"""
    query = select(DocumentSignature).options(
        selectinload(DocumentSignature.doctor)
    ).filter(
        DocumentSignature.id == signature_id,
        DocumentSignature.clinic_id == current_user.clinic_id
    )
    
    result = await db.execute(query)
    signature = result.scalar_one_or_none()
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signature not found"
        )
    
    return DocumentSignatureResponse(
        id=signature.id,
        document_type=signature.document_type,
        document_id=signature.document_id,
        doctor_id=signature.doctor_id,
        clinic_id=signature.clinic_id,
        crm_number=signature.crm_number,
        crm_state=signature.crm_state,
        certificate_serial=signature.certificate_serial,
        certificate_issuer=signature.certificate_issuer,
        certificate_valid_from=signature.certificate_valid_from,
        certificate_valid_to=signature.certificate_valid_to,
        document_hash=signature.document_hash,
        signature_algorithm=signature.signature_algorithm,
        status=signature.status,
        signed_at=signature.signed_at,
        revoked_at=signature.revoked_at,
        revocation_reason=signature.revocation_reason,
        created_at=signature.created_at,
        updated_at=signature.updated_at,
        doctor_name=f"{signature.doctor.first_name or ''} {signature.doctor.last_name or ''}".strip() if signature.doctor else None
    )


@router.get("", response_model=List[DocumentSignatureResponse])
async def list_signatures(
    document_type: Optional[DocumentType] = None,
    document_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """List signatures with optional filters"""
    query = select(DocumentSignature).options(
        selectinload(DocumentSignature.doctor)
    ).filter(
        DocumentSignature.clinic_id == current_user.clinic_id
    )
    
    # Apply filters
    if document_type:
        query = query.filter(DocumentSignature.document_type == document_type)
    if document_id:
        query = query.filter(DocumentSignature.document_id == document_id)
    if doctor_id:
        query = query.filter(DocumentSignature.doctor_id == doctor_id)
    
    # Patients can only see their own document signatures
    if current_user.role == UserRole.PATIENT:
        # This would need to be implemented based on document ownership
        # For now, restrict to doctor/admin/secretary
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    result = await db.execute(query.order_by(DocumentSignature.signed_at.desc()))
    signatures = result.scalars().all()
    
    return [
        DocumentSignatureResponse(
            id=sig.id,
            document_type=sig.document_type,
            document_id=sig.document_id,
            doctor_id=sig.doctor_id,
            clinic_id=sig.clinic_id,
            crm_number=sig.crm_number,
            crm_state=sig.crm_state,
            certificate_serial=sig.certificate_serial,
            certificate_issuer=sig.certificate_issuer,
            certificate_valid_from=sig.certificate_valid_from,
            certificate_valid_to=sig.certificate_valid_to,
            document_hash=sig.document_hash,
            signature_algorithm=sig.signature_algorithm,
            status=sig.status,
            signed_at=sig.signed_at,
            revoked_at=sig.revoked_at,
            revocation_reason=sig.revocation_reason,
            created_at=sig.created_at,
            updated_at=sig.updated_at,
            doctor_name=f"{sig.doctor.first_name or ''} {sig.doctor.last_name or ''}".strip() if sig.doctor else None
        )
        for sig in signatures
    ]


@router.post("/verify", response_model=DocumentSignatureVerifyResponse)
async def verify_signature(
    verify_request: DocumentSignatureVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Verify a document signature"""
    query = select(DocumentSignature).options(
        selectinload(DocumentSignature.doctor)
    ).filter(
        DocumentSignature.document_type == verify_request.document_type,
        DocumentSignature.document_id == verify_request.document_id,
        DocumentSignature.clinic_id == current_user.clinic_id,
        DocumentSignature.status == SignatureStatus.SIGNED
    ).order_by(DocumentSignature.signed_at.desc())
    
    result = await db.execute(query)
    signature = result.scalar_one_or_none()
    
    if not signature:
        return DocumentSignatureVerifyResponse(
            is_valid=False,
            error="Signature not found"
        )
    
    # Verify hash if provided
    if verify_request.document_hash:
        if signature.document_hash != verify_request.document_hash:
            return DocumentSignatureVerifyResponse(
                is_valid=False,
                error="Document hash does not match signature"
            )
    
    # Verify signature cryptographically (if public key available)
    verification_result = DigitalSignatureService.verify_signature(
        signature.document_hash,
        signature.signature_data
    )
    
    if not verification_result.get('is_valid', False):
        return DocumentSignatureVerifyResponse(
            is_valid=False,
            signature=DocumentSignatureResponse(
                id=signature.id,
                document_type=signature.document_type,
                document_id=signature.document_id,
                doctor_id=signature.doctor_id,
                clinic_id=signature.clinic_id,
                crm_number=signature.crm_number,
                crm_state=signature.crm_state,
                certificate_serial=signature.certificate_serial,
                certificate_issuer=signature.certificate_issuer,
                certificate_valid_from=signature.certificate_valid_from,
                certificate_valid_to=signature.certificate_valid_to,
                document_hash=signature.document_hash,
                signature_algorithm=signature.signature_algorithm,
                status=signature.status,
                signed_at=signature.signed_at,
                revoked_at=signature.revoked_at,
                revocation_reason=signature.revocation_reason,
                created_at=signature.created_at,
                updated_at=signature.updated_at,
                doctor_name=f"{signature.doctor.first_name or ''} {signature.doctor.last_name or ''}".strip() if signature.doctor else None
            ),
            error=verification_result.get('error')
        )
    
    return DocumentSignatureVerifyResponse(
        is_valid=True,
        signature=DocumentSignatureResponse(
            id=signature.id,
            document_type=signature.document_type,
            document_id=signature.document_id,
            doctor_id=signature.doctor_id,
            clinic_id=signature.clinic_id,
            crm_number=signature.crm_number,
            crm_state=signature.crm_state,
            certificate_serial=signature.certificate_serial,
            certificate_issuer=signature.certificate_issuer,
            certificate_valid_from=signature.certificate_valid_from,
            certificate_valid_to=signature.certificate_valid_to,
            document_hash=signature.document_hash,
            signature_algorithm=signature.signature_algorithm,
            status=signature.status,
            signed_at=signature.signed_at,
            revoked_at=signature.revoked_at,
            revocation_reason=signature.revocation_reason,
            created_at=signature.created_at,
            updated_at=signature.updated_at,
            doctor_name=f"{signature.doctor.first_name or ''} {signature.doctor.last_name or ''}".strip() if signature.doctor else None
        ),
        message="Signature is valid"
    )


@router.post("/{signature_id}/revoke", response_model=DocumentSignatureResponse)
async def revoke_signature(
    signature_id: int,
    revoke_request: DocumentSignatureRevokeRequest,
    current_user: User = Depends(require_doctor),
    db: AsyncSession = Depends(get_async_session)
):
    """Revoke a signature (only by the signing doctor or admin)"""
    query = select(DocumentSignature).filter(
        DocumentSignature.id == signature_id,
        DocumentSignature.clinic_id == current_user.clinic_id
    )
    
    result = await db.execute(query)
    signature = result.scalar_one_or_none()
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signature not found"
        )
    
    # Check if user can revoke (must be the signing doctor or admin)
    if current_user.role != UserRole.ADMIN and signature.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the signing doctor or admin can revoke this signature"
        )
    
    if signature.status == SignatureStatus.REVOKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signature is already revoked"
        )
    
    # Revoke signature
    signature.status = SignatureStatus.REVOKED
    signature.revoked_at = datetime.now(timezone.utc)
    signature.revocation_reason = revoke_request.revocation_reason
    
    await db.commit()
    await db.refresh(signature, ["doctor"])
    
    return DocumentSignatureResponse(
        id=signature.id,
        document_type=signature.document_type,
        document_id=signature.document_id,
        doctor_id=signature.doctor_id,
        clinic_id=signature.clinic_id,
        crm_number=signature.crm_number,
        crm_state=signature.crm_state,
        certificate_serial=signature.certificate_serial,
        certificate_issuer=signature.certificate_issuer,
        certificate_valid_from=signature.certificate_valid_from,
        certificate_valid_to=signature.certificate_valid_to,
        document_hash=signature.document_hash,
        signature_algorithm=signature.signature_algorithm,
        status=signature.status,
        signed_at=signature.signed_at,
        revoked_at=signature.revoked_at,
        revocation_reason=signature.revocation_reason,
        created_at=signature.created_at,
        updated_at=signature.updated_at,
        doctor_name=f"{signature.doctor.first_name or ''} {signature.doctor.last_name or ''}".strip() if signature.doctor else None
    )
