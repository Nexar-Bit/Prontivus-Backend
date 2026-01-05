"""
Payment Gateway Schemas
"""

from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class PIXPaymentCreate(BaseModel):
    """Request to create a PIX payment"""
    amount: Decimal = Field(..., description="Payment amount", gt=0)
    description: str = Field(..., description="Payment description")
    invoice_id: Optional[int] = Field(None, description="Associated invoice ID")
    appointment_id: Optional[int] = Field(None, description="Associated appointment ID")
    payer_name: Optional[str] = None
    payer_document: Optional[str] = None
    payer_email: Optional[str] = None
    metadata: Optional[dict] = None


class CardPaymentCreate(BaseModel):
    """Request to create a card payment"""
    amount: Decimal = Field(..., description="Payment amount", gt=0)
    description: str = Field(..., description="Payment description")
    card_token: str = Field(..., description="Tokenized card information")
    installments: int = Field(1, description="Number of installments", ge=1, le=12)
    invoice_id: Optional[int] = Field(None, description="Associated invoice ID")
    appointment_id: Optional[int] = Field(None, description="Associated appointment ID")
    payer_name: Optional[str] = None
    payer_document: Optional[str] = None
    payer_email: Optional[str] = None
    metadata: Optional[dict] = None


class PaymentResponse(BaseModel):
    """Payment gateway response"""
    payment_id: str
    transaction_id: str
    status: str  # pending, completed, failed, cancelled
    amount: float
    currency: str
    payment_method: str
    qr_code: Optional[str] = None  # For PIX
    qr_code_image: Optional[str] = None  # Base64 encoded QR Code image
    expiration_time: Optional[float] = None  # Unix timestamp
    installments: Optional[int] = None
    card_last_4: Optional[str] = None
    card_brand: Optional[str] = None
    paid_at: Optional[str] = None
    created_at: str


class PaymentStatusResponse(BaseModel):
    """Payment status response"""
    transaction_id: str
    status: str
    paid_at: Optional[str] = None
    amount: float
    currency: str


class PaymentCancelRequest(BaseModel):
    """Request to cancel a payment"""
    reason: Optional[str] = None


class PaymentRefundRequest(BaseModel):
    """Request to refund a payment"""
    amount: Optional[Decimal] = Field(None, description="Refund amount (if None, full refund)", gt=0)
    reason: Optional[str] = None


class PaymentRefundResponse(BaseModel):
    """Refund response"""
    transaction_id: str
    refund_id: str
    status: str
    refunded_amount: float
    refunded_at: str
    reason: Optional[str] = None
