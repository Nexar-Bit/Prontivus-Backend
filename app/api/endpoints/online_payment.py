"""
Online Payment API Endpoints
Handles online payment processing for consultations and invoices
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timezone
from decimal import Decimal
import logging

from database import get_async_session
from app.core.auth import get_current_user, RoleChecker
from app.models import User, UserRole, Patient, Invoice, Appointment
from app.models.financial import Payment, PaymentMethod, PaymentStatus
from app.schemas.payment_gateway import (
    PIXPaymentCreate,
    CardPaymentCreate,
    PaymentResponse,
    PaymentStatusResponse,
    PaymentCancelRequest,
    PaymentRefundRequest,
    PaymentRefundResponse
)
from app.services.payment_gateway import get_payment_gateway_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/online-payments", tags=["Online Payments"])

# Role checkers
require_patient = RoleChecker([UserRole.PATIENT])
require_doctor = RoleChecker([UserRole.DOCTOR, UserRole.ADMIN])
require_authenticated = RoleChecker([UserRole.PATIENT, UserRole.DOCTOR, UserRole.ADMIN, UserRole.SECRETARY])


@router.post("/pix", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_pix_payment(
    payment_data: PIXPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a PIX payment for an invoice or appointment
    
    Patients can pay their own invoices/appointments
    Staff can create payments for any invoice/appointment in their clinic
    """
    try:
        # Verify invoice or appointment exists and user has access
        if payment_data.invoice_id:
            invoice_query = select(Invoice).filter(
                Invoice.id == payment_data.invoice_id,
                Invoice.clinic_id == current_user.clinic_id
            )
            invoice_result = await db.execute(invoice_query)
            invoice = invoice_result.scalar_one_or_none()
            
            if not invoice:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invoice not found"
                )
            
            # Patients can only pay their own invoices
            if current_user.role == UserRole.PATIENT:
                patient_query = select(Patient).filter(
                    and_(
                        Patient.email == current_user.email,
                        Patient.clinic_id == current_user.clinic_id
                    )
                )
                patient_result = await db.execute(patient_query)
                patient = patient_result.scalar_one_or_none()
                
                if not patient or invoice.patient_id != patient.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You can only pay your own invoices"
                    )
            
            amount = invoice.total_amount
            description = f"Pagamento de fatura #{invoice.id}"
            
        elif payment_data.appointment_id:
            appointment_query = select(Appointment).filter(
                Appointment.id == payment_data.appointment_id,
                Appointment.clinic_id == current_user.clinic_id
            )
            appointment_result = await db.execute(appointment_query)
            appointment = appointment_result.scalar_one_or_none()
            
            if not appointment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Appointment not found"
                )
            
            # Patients can only pay their own appointments
            if current_user.role == UserRole.PATIENT:
                patient_query = select(Patient).filter(
                    and_(
                        Patient.email == current_user.email,
                        Patient.clinic_id == current_user.clinic_id
                    )
                )
                patient_result = await db.execute(patient_query)
                patient = patient_result.scalar_one_or_none()
                
                if not patient or appointment.patient_id != patient.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You can only pay your own appointments"
                    )
            
            amount = payment_data.amount
            description = f"Pagamento de consulta #{appointment.id}"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either invoice_id or appointment_id must be provided"
            )
        
        # Use provided amount or invoice amount
        payment_amount = payment_data.amount if payment_data.amount else amount
        
        # Create PIX payment via gateway
        payer_info = {
            "name": payment_data.payer_name or current_user.full_name,
            "document": payment_data.payer_document,
            "email": payment_data.payer_email or current_user.email
        }
        
        metadata = payment_data.metadata or {}
        if payment_data.invoice_id:
            metadata["invoice_id"] = payment_data.invoice_id
        if payment_data.appointment_id:
            metadata["appointment_id"] = payment_data.appointment_id
        
        payment_gateway = get_payment_gateway_service()
        gateway_response = await payment_gateway.create_pix_payment(
            amount=payment_amount,
            description=description,
            payer_info=payer_info,
            metadata=metadata
        )
        
        # Create payment record in database
        db_payment = Payment(
            invoice_id=payment_data.invoice_id,
            amount=payment_amount,
            method=PaymentMethod.PIX,
            status=PaymentStatus.PENDING,
            reference_number=gateway_response["transaction_id"],
            notes=f"PIX Payment - {description}",
            created_by=current_user.id if current_user.role != UserRole.PATIENT else None
        )
        db.add(db_payment)
        await db.flush()
        await db.commit()
        
        return PaymentResponse(
            payment_id=gateway_response["payment_id"],
            transaction_id=gateway_response["transaction_id"],
            status=gateway_response["status"],
            amount=gateway_response["amount"],
            currency=gateway_response["currency"],
            payment_method=gateway_response["payment_method"],
            qr_code=gateway_response["qr_code"],
            qr_code_image=gateway_response.get("qr_code_image"),
            expiration_time=gateway_response.get("expiration_time"),
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating PIX payment: {str(e)}"
        )


@router.post("/card", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_card_payment(
    payment_data: CardPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a credit/debit card payment for an invoice or appointment
    """
    try:
        # Similar validation as PIX payment
        if payment_data.invoice_id:
            invoice_query = select(Invoice).filter(
                Invoice.id == payment_data.invoice_id,
                Invoice.clinic_id == current_user.clinic_id
            )
            invoice_result = await db.execute(invoice_query)
            invoice = invoice_result.scalar_one_or_none()
            
            if not invoice:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invoice not found"
                )
            
            if current_user.role == UserRole.PATIENT:
                patient_query = select(Patient).filter(
                    and_(
                        Patient.email == current_user.email,
                        Patient.clinic_id == current_user.clinic_id
                    )
                )
                patient_result = await db.execute(patient_query)
                patient = patient_result.scalar_one_or_none()
                
                if not patient or invoice.patient_id != patient.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You can only pay your own invoices"
                    )
            
            amount = invoice.total_amount
            description = f"Pagamento de fatura #{invoice.id}"
        elif payment_data.appointment_id:
            appointment_query = select(Appointment).filter(
                Appointment.id == payment_data.appointment_id,
                Appointment.clinic_id == current_user.clinic_id
            )
            appointment_result = await db.execute(appointment_query)
            appointment = appointment_result.scalar_one_or_none()
            
            if not appointment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Appointment not found"
                )
            
            if current_user.role == UserRole.PATIENT:
                patient_query = select(Patient).filter(
                    and_(
                        Patient.email == current_user.email,
                        Patient.clinic_id == current_user.clinic_id
                    )
                )
                patient_result = await db.execute(patient_query)
                patient = patient_result.scalar_one_or_none()
                
                if not patient or appointment.patient_id != patient.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You can only pay your own appointments"
                    )
            
            amount = payment_data.amount
            description = f"Pagamento de consulta #{payment_data.appointment_id}"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either invoice_id or appointment_id must be provided"
            )
        
        payment_amount = payment_data.amount if payment_data.amount else amount
        
        # Create card payment via gateway
        payer_info = {
            "name": payment_data.payer_name or current_user.full_name,
            "document": payment_data.payer_document,
            "email": payment_data.payer_email or current_user.email
        }
        
        metadata = payment_data.metadata or {}
        if payment_data.invoice_id:
            metadata["invoice_id"] = payment_data.invoice_id
        if payment_data.appointment_id:
            metadata["appointment_id"] = payment_data.appointment_id
        
        payment_gateway = get_payment_gateway_service()
        gateway_response = await payment_gateway.create_card_payment(
            amount=payment_amount,
            description=description,
            card_token=payment_data.card_token,
            installments=payment_data.installments,
            payer_info=payer_info,
            metadata=metadata
        )
        
        # Create payment record
        payment_method = PaymentMethod.CREDIT_CARD if payment_data.installments > 1 else PaymentMethod.DEBIT_CARD
        
        db_payment = Payment(
            invoice_id=payment_data.invoice_id,
            amount=payment_amount,
            method=payment_method,
            status=PaymentStatus.PENDING,
            reference_number=gateway_response["transaction_id"],
            notes=f"Card Payment ({payment_data.installments}x) - {description}",
            created_by=current_user.id if current_user.role != UserRole.PATIENT else None
        )
        db.add(db_payment)
        await db.flush()
        await db.commit()
        
        return PaymentResponse(
            payment_id=gateway_response["payment_id"],
            transaction_id=gateway_response["transaction_id"],
            status=gateway_response["status"],
            amount=gateway_response["amount"],
            currency=gateway_response["currency"],
            payment_method=gateway_response["payment_method"],
            installments=gateway_response.get("installments"),
            card_last_4=gateway_response.get("card_last_4"),
            card_brand=gateway_response.get("card_brand"),
            paid_at=gateway_response.get("paid_at"),
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating card payment: {str(e)}"
        )


@router.get("/status/{transaction_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Check payment status"""
    # Verify user has access to this payment
    payment_query = select(Payment).join(Invoice).filter(
        and_(
            Payment.reference_number == transaction_id,
            Invoice.clinic_id == current_user.clinic_id
        )
    )
    
    payment_result = await db.execute(payment_query)
    payment = payment_result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Check status from gateway
    payment_gateway = get_payment_gateway_service()
    gateway_status = await payment_gateway.check_payment_status(transaction_id)
    
    # Update payment status if changed
    if gateway_status["status"] == "completed" and payment.status != PaymentStatus.COMPLETED:
        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = datetime.fromisoformat(gateway_status["paid_at"].replace('Z', '+00:00'))
        await db.commit()
    
    return PaymentStatusResponse(
        transaction_id=transaction_id,
        status=gateway_status["status"],
        paid_at=gateway_status.get("paid_at"),
        amount=gateway_status["amount"],
        currency=gateway_status["currency"]
    )


@router.post("/cancel/{transaction_id}")
async def cancel_payment(
    transaction_id: str,
    cancel_request: PaymentCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Cancel a pending payment"""
    # Verify payment exists and is pending
    payment_query = select(Payment).join(Invoice).filter(
        and_(
            Payment.reference_number == transaction_id,
            Invoice.clinic_id == current_user.clinic_id,
            Payment.status == PaymentStatus.PENDING
        )
    )
    
    payment_result = await db.execute(payment_query)
    payment = payment_result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending payment not found"
        )
    
    # Cancel via gateway
    payment_gateway = get_payment_gateway_service()
    cancel_result = await payment_gateway.cancel_payment(
        transaction_id,
        cancel_request.reason
    )
    
    # Update payment status
    payment.status = PaymentStatus.CANCELLED
    payment.notes = f"{payment.notes or ''}\nCancelled: {cancel_request.reason or 'No reason provided'}"
    await db.commit()
    
    return cancel_result


@router.post("/refund/{transaction_id}", response_model=PaymentRefundResponse)
async def refund_payment(
    transaction_id: str,
    refund_request: PaymentRefundRequest,
    current_user: User = Depends(require_doctor),
    db: AsyncSession = Depends(get_async_session)
):
    """Refund a payment (staff only)"""
    # Verify payment exists and is completed
    payment_query = select(Payment).join(Invoice).filter(
        and_(
            Payment.reference_number == transaction_id,
            Invoice.clinic_id == current_user.clinic_id,
            Payment.status == PaymentStatus.COMPLETED
        )
    )
    
    payment_result = await db.execute(payment_query)
    payment = payment_result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Completed payment not found"
        )
    
    # Refund via gateway
    payment_gateway = get_payment_gateway_service()
    refund_amount = refund_request.amount if refund_request.amount else payment.amount
    refund_result = await payment_gateway.refund_payment(
        transaction_id,
        refund_amount,
        refund_request.reason
    )
    
    # Update payment status
    payment.status = PaymentStatus.REFUNDED
    payment.notes = f"{payment.notes or ''}\nRefunded: {refund_request.reason or 'No reason provided'}"
    await db.commit()
    
    return PaymentRefundResponse(
        transaction_id=transaction_id,
        refund_id=refund_result["refund_id"],
        status=refund_result["status"],
        refunded_amount=refund_result["refunded_amount"],
        refunded_at=refund_result["refunded_at"],
        reason=refund_result.get("reason")
    )


@router.post("/webhook/{gateway}")
async def payment_webhook(
    gateway: str,
    request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Webhook endpoint for payment gateway notifications
    
    Supported gateways: mercadopago, stripe, pagseguro
    This endpoint receives payment status updates from payment gateways
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        headers = dict(request.headers)
        
        # Verify webhook signature (gateway-specific)
        if gateway.lower() == "mercadopago":
            # Mercado Pago webhook verification
            x_request_id = headers.get("x-request-id")
            x_signature = headers.get("x-signature")
            
            # In production, verify signature using Mercado Pago's verification method
            # For now, we'll process the webhook
            
            import json
            webhook_data = json.loads(body.decode())
            
            # Process webhook data
            if webhook_data.get("type") == "payment":
                payment_data = webhook_data.get("data", {})
                payment_id = payment_data.get("id")
                
                if payment_id:
                    # Update payment status in database
                    payment_query = select(Payment).filter(
                        Payment.reference_number == str(payment_id)
                    )
                    payment_result = await db.execute(payment_query)
                    payment = payment_result.scalar_one_or_none()
                    
                    if payment:
                        # Map Mercado Pago status to our status
                        mp_status = payment_data.get("status", "")
                        status_map = {
                            "pending": PaymentStatus.PENDING,
                            "approved": PaymentStatus.COMPLETED,
                            "authorized": PaymentStatus.COMPLETED,
                            "in_process": PaymentStatus.PENDING,
                            "in_mediation": PaymentStatus.PENDING,
                            "rejected": PaymentStatus.FAILED,
                            "cancelled": PaymentStatus.CANCELLED,
                            "refunded": PaymentStatus.REFUNDED,
                            "charged_back": PaymentStatus.FAILED
                        }
                        
                        new_status = status_map.get(mp_status, PaymentStatus.PENDING)
                        payment.status = new_status
                        
                        if new_status == PaymentStatus.COMPLETED:
                            paid_at = payment_data.get("date_approved") or payment_data.get("date_created")
                            if paid_at:
                                try:
                                    payment.paid_at = datetime.fromisoformat(paid_at.replace('Z', '+00:00'))
                                except:
                                    payment.paid_at = datetime.now(timezone.utc)
                        
                        await db.commit()
                        logger.info(f"Payment {payment_id} status updated to {new_status}")
                        
                        return {"status": "processed", "payment_id": payment_id}
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Error processing payment webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )
