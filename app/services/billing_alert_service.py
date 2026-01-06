"""
Billing Alert Service
Handles alerts for overdue and upcoming invoice due dates
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import Invoice, InvoiceStatus, Payment
from app.models import Patient, User
from sqlalchemy.orm import selectinload
from app.services.email_service import email_service
from app.services.sms_service import sms_service
from app.services.notification_dispatcher import send_notification

logger = logging.getLogger(__name__)


class BillingAlertService:
    """Service for managing billing alerts"""
    
    def __init__(self):
        self.alert_days_before = int(os.getenv("BILLING_ALERT_DAYS_BEFORE", "3"))  # Alert 3 days before due date
        self.overdue_alert_interval = int(os.getenv("BILLING_OVERDUE_ALERT_INTERVAL", "7"))  # Alert every 7 days for overdue
    
    async def check_overdue_invoices(
        self,
        clinic_id: int,
        db: AsyncSession,
        send_notifications: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Check for overdue invoices and send alerts
        
        Args:
            clinic_id: Clinic ID to check
            db: Database session
            send_notifications: Whether to send notifications (default: True)
        
        Returns:
            List of overdue invoice alerts
        """
        now = datetime.now(timezone.utc)
        
        # Find overdue invoices (issued but not paid, past due date)
        query = select(Invoice).options(
            selectinload(Invoice.patient),
            selectinload(Invoice.payments),
        ).filter(
            and_(
                Invoice.clinic_id == clinic_id,
                Invoice.status == InvoiceStatus.ISSUED,
                Invoice.due_date.isnot(None),
                Invoice.due_date < now
            )
        )
        
        result = await db.execute(query)
        invoices = result.unique().scalars().all()
        
        alerts = []
        for invoice in invoices:
            # Calculate days overdue
            days_overdue = (now.date() - invoice.due_date.date()).days if invoice.due_date else 0
            
            # Calculate paid amount
            paid_amount = sum(
                payment.amount for payment in invoice.payments 
                if payment.status.value == "completed"
            )
            outstanding_amount = float(invoice.total_amount) - paid_amount
            
            if outstanding_amount > 0:
                alert = {
                    'invoice_id': invoice.id,
                    'patient_id': invoice.patient_id,
                    'patient_name': invoice.patient.full_name if invoice.patient else 'Unknown',
                    'patient_email': invoice.patient.email if invoice.patient else None,
                    'patient_phone': invoice.patient.phone if invoice.patient else None,
                    'total_amount': float(invoice.total_amount),
                    'outstanding_amount': outstanding_amount,
                    'due_date': invoice.due_date,
                    'days_overdue': days_overdue,
                    'issue_date': invoice.issue_date,
                }
                alerts.append(alert)
                
                # Send notifications if enabled
                if send_notifications and invoice.patient:
                    await self._send_overdue_alert(invoice, days_overdue, outstanding_amount, db)
        
        return alerts
    
    async def check_upcoming_due_dates(
        self,
        clinic_id: int,
        db: AsyncSession,
        send_notifications: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Check for invoices with upcoming due dates and send alerts
        
        Args:
            clinic_id: Clinic ID to check
            db: Database session
            send_notifications: Whether to send notifications (default: True)
        
        Returns:
            List of upcoming invoice alerts
        """
        now = datetime.now(timezone.utc)
        alert_date = now + timedelta(days=self.alert_days_before)
        
        # Find invoices due in the next N days
        query = select(Invoice).options(
            selectinload(Invoice.patient),
            selectinload(Invoice.payments),
        ).filter(
            and_(
                Invoice.clinic_id == clinic_id,
                Invoice.status == InvoiceStatus.ISSUED,
                Invoice.due_date.isnot(None),
                Invoice.due_date >= now,
                Invoice.due_date <= alert_date
            )
        )
        
        result = await db.execute(query)
        invoices = result.unique().scalars().all()
        
        alerts = []
        for invoice in invoices:
            # Calculate days until due
            days_until_due = (invoice.due_date.date() - now.date()).days if invoice.due_date else 0
            
            # Calculate paid amount
            paid_amount = sum(
                payment.amount for payment in invoice.payments 
                if payment.status.value == "completed"
            )
            outstanding_amount = float(invoice.total_amount) - paid_amount
            
            if outstanding_amount > 0:
                alert = {
                    'invoice_id': invoice.id,
                    'patient_id': invoice.patient_id,
                    'patient_name': invoice.patient.full_name if invoice.patient else 'Unknown',
                    'patient_email': invoice.patient.email if invoice.patient else None,
                    'patient_phone': invoice.patient.phone if invoice.patient else None,
                    'total_amount': float(invoice.total_amount),
                    'outstanding_amount': outstanding_amount,
                    'due_date': invoice.due_date,
                    'days_until_due': days_until_due,
                    'issue_date': invoice.issue_date,
                }
                alerts.append(alert)
                
                # Send notifications if enabled
                if send_notifications and invoice.patient:
                    await self._send_upcoming_due_alert(invoice, days_until_due, outstanding_amount, db)
        
        return alerts
    
    async def _send_overdue_alert(
        self,
        invoice: Invoice,
        days_overdue: int,
        outstanding_amount: float,
        db: AsyncSession
    ):
        """Send alert for overdue invoice"""
        try:
            patient = invoice.patient
            if not patient:
                return
            
            # Get frontend URL
            frontend_url = os.getenv("FRONTEND_URL", "https://prontivus-frontend-p2rr.vercel.app")
            invoice_url = f"{frontend_url}/portal/billing/{invoice.id}"
            
            due_date_str = invoice.due_date.strftime("%d/%m/%Y") if invoice.due_date else "N/A"
            
            # Send email
            if patient.email:
                html_body = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #dc2626; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                        .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
                        .alert-box {{ background-color: #fee2e2; border-left: 4px solid #dc2626; padding: 20px; margin: 20px 0; }}
                        .info-box {{ background-color: white; padding: 20px; margin: 20px 0; border-left: 4px solid #dc2626; }}
                        .info-item {{ margin: 10px 0; padding: 8px; }}
                        .info-label {{ font-weight: bold; color: #dc2626; }}
                        .amount {{ font-size: 24px; font-weight: bold; color: #dc2626; }}
                        .button {{ display: inline-block; padding: 12px 24px; background-color: #dc2626; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>⚠️ Fatura Vencida</h1>
                        </div>
                        <div class="content">
                            <p>Olá <strong>{patient.first_name}</strong>,</p>
                            
                            <div class="alert-box">
                                <p><strong>Atenção!</strong> Você possui uma fatura vencida há <strong>{days_overdue} dia(s)</strong>.</p>
                            </div>
                            
                            <div class="info-box">
                                <div class="info-item">
                                    <span class="info-label">Número da Fatura:</span> #{invoice.id}
                                </div>
                                <div class="info-item">
                                    <span class="info-label">Data de Vencimento:</span> {due_date_str}
                                </div>
                                <div class="info-item">
                                    <span class="info-label">Valor Total:</span> R$ {outstanding_amount:,.2f}
                                </div>
                                <div class="info-item">
                                    <span class="info-label">Dias em Atraso:</span> {days_overdue} dia(s)
                                </div>
                            </div>
                            
                            <p style="text-align: center;">
                                <a href="{invoice_url}" class="button">Ver Fatura e Pagar</a>
                            </p>
                            
                            <p>Por favor, entre em contato conosco para regularizar sua situação ou efetue o pagamento o quanto antes.</p>
                        </div>
                        <div class="footer">
                            <p>Este é um e-mail automático. Por favor, não responda a esta mensagem.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                text_body = (
                    f"Fatura Vencida\n\n"
                    f"Olá {patient.first_name},\n\n"
                    f"ATENÇÃO! Você possui uma fatura vencida há {days_overdue} dia(s).\n\n"
                    f"DADOS DA FATURA:\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Número: #{invoice.id}\n"
                    f"Data de Vencimento: {due_date_str}\n"
                    f"Valor: R$ {outstanding_amount:,.2f}\n"
                    f"Dias em Atraso: {days_overdue} dia(s)\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Por favor, entre em contato conosco para regularizar sua situação.\n\n"
                    f"Ver fatura: {invoice_url}\n\n"
                    f"---\n"
                    f"Este é um e-mail automático."
                )
                
                await email_service.send_email(
                    to_email=patient.email,
                    subject=f"⚠️ Fatura Vencida - #{invoice.id} - {days_overdue} dia(s) em atraso",
                    html_body=html_body,
                    text_body=text_body,
                )
            
            # Send SMS if enabled
            if patient.phone:
                sms_message = (
                    f"Prontivus: Fatura #{invoice.id} vencida há {days_overdue} dia(s). "
                    f"Valor: R$ {outstanding_amount:,.2f}. "
                    f"Por favor, entre em contato para regularizar."
                )
                # Get patient user account if exists for SMS notification check
                patient_user_query = select(User).filter(
                    and_(
                        User.email == patient.email,
                        User.clinic_id == invoice.clinic_id
                    )
                )
                patient_user_result = await db.execute(patient_user_query)
                patient_user = patient_user_result.scalar_one_or_none()
                
                if patient_user:
                    from app.services.sms_service import send_notification_sms_if_enabled
                    await send_notification_sms_if_enabled(
                        user_id=patient_user.id,
                        user_phone=patient.phone,
                        notification_title="Fatura Vencida",
                        notification_message=sms_message,
                        db=db,
                    )
                else:
                    # Send SMS directly if no user account found
                    await sms_service.send_sms(
                        to_phone=patient.phone,
                        message=sms_message,
                    )
            
            # Send in-app notification
            # Get patient user account if exists
            patient_user_query = select(User).filter(
                and_(
                    User.email == patient.email,
                    User.clinic_id == invoice.clinic_id
                )
            )
            patient_user_result = await db.execute(patient_user_query)
            patient_user = patient_user_result.scalar_one_or_none()
            
            if patient_user:
                await send_notification(
                    user_id=patient_user.id,
                    notification_title=f"Fatura Vencida - {days_overdue} dia(s) em atraso",
                    notification_message=f"Fatura #{invoice.id} no valor de R$ {outstanding_amount:,.2f} está vencida há {days_overdue} dia(s).",
                    notification_type="warning",
                    notification_category="systemUpdates",
                    action_url=f"/portal/billing/{invoice.id}",
                    db=db,
                )
        
        except Exception as e:
            logger.error(f"Failed to send overdue alert for invoice {invoice.id}: {str(e)}")
    
    async def _send_upcoming_due_alert(
        self,
        invoice: Invoice,
        days_until_due: int,
        outstanding_amount: float,
        db: AsyncSession
    ):
        """Send alert for upcoming invoice due date"""
        try:
            patient = invoice.patient
            if not patient:
                return
            
            # Get frontend URL
            frontend_url = os.getenv("FRONTEND_URL", "https://prontivus-frontend-p2rr.vercel.app")
            invoice_url = f"{frontend_url}/portal/billing/{invoice.id}"
            
            due_date_str = invoice.due_date.strftime("%d/%m/%Y") if invoice.due_date else "N/A"
            
            # Send email
            if patient.email:
                html_body = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #f59e0b; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                        .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #ddd; }}
                        .reminder-box {{ background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 20px; margin: 20px 0; }}
                        .info-box {{ background-color: white; padding: 20px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
                        .info-item {{ margin: 10px 0; padding: 8px; }}
                        .info-label {{ font-weight: bold; color: #f59e0b; }}
                        .button {{ display: inline-block; padding: 12px 24px; background-color: #f59e0b; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>📅 Lembrete de Fatura</h1>
                        </div>
                        <div class="content">
                            <p>Olá <strong>{patient.first_name}</strong>,</p>
                            
                            <div class="reminder-box">
                                <p><strong>Lembrete:</strong> Você possui uma fatura com vencimento em <strong>{days_until_due} dia(s)</strong>.</p>
                            </div>
                            
                            <div class="info-box">
                                <div class="info-item">
                                    <span class="info-label">Número da Fatura:</span> #{invoice.id}
                                </div>
                                <div class="info-item">
                                    <span class="info-label">Data de Vencimento:</span> {due_date_str}
                                </div>
                                <div class="info-item">
                                    <span class="info-label">Valor:</span> R$ {outstanding_amount:,.2f}
                                </div>
                            </div>
                            
                            <p style="text-align: center;">
                                <a href="{invoice_url}" class="button">Ver Fatura e Pagar</a>
                            </p>
                            
                            <p>Evite atrasos e multas. Efetue o pagamento antes do vencimento.</p>
                        </div>
                        <div class="footer">
                            <p>Este é um e-mail automático. Por favor, não responda a esta mensagem.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                text_body = (
                    f"Lembrete de Fatura\n\n"
                    f"Olá {patient.first_name},\n\n"
                    f"Lembrete: Você possui uma fatura com vencimento em {days_until_due} dia(s).\n\n"
                    f"DADOS DA FATURA:\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Número: #{invoice.id}\n"
                    f"Data de Vencimento: {due_date_str}\n"
                    f"Valor: R$ {outstanding_amount:,.2f}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Evite atrasos e multas. Efetue o pagamento antes do vencimento.\n\n"
                    f"Ver fatura: {invoice_url}\n\n"
                    f"---\n"
                    f"Este é um e-mail automático."
                )
                
                await email_service.send_email(
                    to_email=patient.email,
                    subject=f"📅 Lembrete: Fatura #{invoice.id} vence em {days_until_due} dia(s)",
                    html_body=html_body,
                    text_body=text_body,
                )
            
            # Send SMS if enabled
            if patient.phone:
                sms_message = (
                    f"Prontivus: Lembrete - Fatura #{invoice.id} vence em {days_until_due} dia(s). "
                    f"Valor: R$ {outstanding_amount:,.2f}. "
                    f"Evite atrasos, efetue o pagamento antes do vencimento."
                )
                # Get patient user account if exists for SMS notification check
                patient_user_query = select(User).filter(
                    and_(
                        User.email == patient.email,
                        User.clinic_id == invoice.clinic_id
                    )
                )
                patient_user_result = await db.execute(patient_user_query)
                patient_user = patient_user_result.scalar_one_or_none()
                
                if patient_user:
                    from app.services.sms_service import send_notification_sms_if_enabled
                    await send_notification_sms_if_enabled(
                        user_id=patient_user.id,
                        user_phone=patient.phone,
                        notification_title="Lembrete de Fatura",
                        notification_message=sms_message,
                        db=db,
                    )
                else:
                    # Send SMS directly if no user account found
                    await sms_service.send_sms(
                        to_phone=patient.phone,
                        message=sms_message,
                    )
            
            # Send in-app notification
            patient_user_query = select(User).filter(
                and_(
                    User.email == patient.email,
                    User.clinic_id == invoice.clinic_id
                )
            )
            patient_user_result = await db.execute(patient_user_query)
            patient_user = patient_user_result.scalar_one_or_none()
            
            if patient_user:
                await send_notification(
                    user_id=patient_user.id,
                    notification_title=f"Fatura vence em {days_until_due} dia(s)",
                    notification_message=f"Fatura #{invoice.id} no valor de R$ {outstanding_amount:,.2f} vence em {days_until_due} dia(s).",
                    notification_type="info",
                    notification_category="systemUpdates",
                    action_url=f"/portal/billing/{invoice.id}",
                    db=db,
                )
        
        except Exception as e:
            logger.error(f"Failed to send upcoming due alert for invoice {invoice.id}: {str(e)}")


# Global billing alert service instance
billing_alert_service = BillingAlertService()
