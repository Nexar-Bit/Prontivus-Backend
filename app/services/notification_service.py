"""
Comprehensive Notification Service
Handles all email notifications for SMTP Authentication, Operations, and Financial events
"""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime
from jinja2 import Template

from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class NotificationService:
    """Centralized notification service for all email types"""
    
    def __init__(self):
        self.email_service = EmailService()
    
    # ========== SMTP Authentication & Security Emails ==========
    
    async def send_email_verification(
        self,
        email: str,
        name: str,
        verification_token: str,
        frontend_url: str
    ) -> bool:
        """Send email verification/confirmation"""
        verification_link = f"{frontend_url}/auth/verify-email?token={verification_token}"
        
        subject = "Confirmação de Cadastro - Prontivus"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #4F46E5; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Prontivus</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Bem-vindo ao Prontivus. Para ativar sua conta, clique no botão abaixo:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_link}" 
                       style="background-color: #4F46E5; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Confirmar E-mail
                    </a>
                </div>
                
                <p>Ou copie e cole este link no seu navegador:</p>
                <p style="word-break: break-all; color: #6B7280;">{verification_link}</p>
                
                <p style="color: #6B7280; font-size: 14px; margin-top: 30px;">
                    Este link expira em 24 horas.
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_password_recovery(
        self,
        email: str,
        name: str,
        reset_token: str,
        frontend_url: str
    ) -> bool:
        """Send password recovery email"""
        reset_link = f"{frontend_url}/auth/reset-password?token={reset_token}"
        
        subject = "Recuperação de Senha - Prontivus"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #4F46E5; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Prontivus</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Recebemos uma solicitação para redefinir sua senha.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" 
                       style="background-color: #4F46E5; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Redefinir Senha
                    </a>
                </div>
                
                <p>Ou copie e cole este link no seu navegador:</p>
                <p style="word-break: break-all; color: #6B7280;">{reset_link}</p>
                
                <p style="color: #DC2626; margin-top: 20px;">
                    <strong>Não solicitou essa alteração?</strong><br>
                    Ignore este e-mail. Sua senha não será alterada.
                </p>
                
                <p style="color: #6B7280; font-size: 14px; margin-top: 30px;">
                    Este link expira em 1 hora por segurança.
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_password_changed(
        self,
        email: str,
        name: str
    ) -> bool:
        """Send notification when password is changed successfully"""
        subject = "Senha Alterada com Sucesso - Prontivus"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #10B981; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">✓ Senha Alterada</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Sua senha foi alterada com sucesso em {datetime.now().strftime('%d/%m/%Y às %H:%M')}.</p>
                
                <p style="color: #DC2626; margin-top: 20px;">
                    <strong>Não foi você?</strong><br>
                    Entre em contato conosco imediatamente em suporte@prontivus.com
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_new_login_detected(
        self,
        email: str,
        name: str,
        ip_address: Optional[str] = None,
        device: Optional[str] = None,
        location: Optional[str] = None
    ) -> bool:
        """Send notification when new login is detected (optional, adds trust)"""
        subject = "Novo Login Detectado - Prontivus"
        
        login_details = []
        if ip_address:
            login_details.append(f"<li><strong>IP:</strong> {ip_address}</li>")
        if device:
            login_details.append(f"<li><strong>Dispositivo:</strong> {device}</li>")
        if location:
            login_details.append(f"<li><strong>Localização:</strong> {location}</li>")
        
        details_html = "".join(login_details) if login_details else "<li>Informações não disponíveis</li>"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #F59E0B; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">⚠ Novo Login Detectado</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Detectamos um novo login em sua conta em {datetime.now().strftime('%d/%m/%Y às %H:%M')}.</p>
                
                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Detalhes do Login:</h3>
                    <ul>
                        {details_html}
                        <li><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M')}</li>
                    </ul>
                </div>
                
                <p style="color: #DC2626;">
                    <strong>Não foi você?</strong><br>
                    Altere sua senha imediatamente e entre em contato conosco.
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    # ========== Operational & Functional Emails ==========
    
    async def send_appointment_scheduled(
        self,
        email: str,
        name: str,
        appointment_date: datetime,
        doctor_name: str,
        appointment_type: str = "Consulta"
    ) -> bool:
        """Send notification when appointment is scheduled"""
        subject = f"Consulta Agendada - {appointment_date.strftime('%d/%m/%Y')}"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #10B981; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">✓ Consulta Agendada</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Sua consulta foi agendada com sucesso!</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3>Detalhes da Consulta:</h3>
                    <p><strong>Tipo:</strong> {appointment_type}</p>
                    <p><strong>Data:</strong> {appointment_date.strftime('%d/%m/%Y')}</p>
                    <p><strong>Horário:</strong> {appointment_date.strftime('%H:%M')}</p>
                    <p><strong>Médico:</strong> {doctor_name}</p>
                </div>
                
                <p style="color: #6B7280;">
                    Lembre-se de chegar com 15 minutos de antecedência.
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_appointment_changed(
        self,
        email: str,
        name: str,
        old_date: datetime,
        new_date: datetime,
        doctor_name: str
    ) -> bool:
        """Send notification when appointment is changed"""
        subject = f"Consulta Alterada - Nova data: {new_date.strftime('%d/%m/%Y')}"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #F59E0B; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Consulta Alterada</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Sua consulta foi alterada:</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3>❌ Data Anterior:</h3>
                    <p>{old_date.strftime('%d/%m/%Y às %H:%M')}</p>
                    
                    <h3 style="margin-top: 20px;">✓ Nova Data:</h3>
                    <p><strong>{new_date.strftime('%d/%m/%Y às %H:%M')}</strong></p>
                    <p><strong>Médico:</strong> {doctor_name}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_appointment_cancelled(
        self,
        email: str,
        name: str,
        appointment_date: datetime,
        doctor_name: str,
        reason: Optional[str] = None
    ) -> bool:
        """Send notification when appointment is cancelled"""
        subject = f"Consulta Cancelada - {appointment_date.strftime('%d/%m/%Y')}"
        
        reason_html = f"<p><strong>Motivo:</strong> {reason}</p>" if reason else ""
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #DC2626; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Consulta Cancelada</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Sua consulta foi cancelada:</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Data:</strong> {appointment_date.strftime('%d/%m/%Y às %H:%M')}</p>
                    <p><strong>Médico:</strong> {doctor_name}</p>
                    {reason_html}
                </div>
                
                <p>Para reagendar, entre em contato conosco.</p>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_signature_created(
        self,
        email: str,
        name: str,
        document_type: str,
        document_date: datetime
    ) -> bool:
        """Send notification when digital signature is created"""
        subject = "Assinatura Digital Criada - Prontivus"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #10B981; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">✓ Assinatura Criada</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Uma assinatura digital foi criada:</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Documento:</strong> {document_type}</p>
                    <p><strong>Data:</strong> {document_date.strftime('%d/%m/%Y às %H:%M')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    # ========== Financial Emails ==========
    
    async def send_invoice_generated(
        self,
        email: str,
        name: str,
        invoice_number: str,
        amount: float,
        due_date: datetime,
        payment_link: Optional[str] = None
    ) -> bool:
        """Send notification when invoice is generated"""
        subject = f"Fatura Gerada - #{invoice_number}"
        
        payment_button = ""
        if payment_link:
            payment_button = f"""
            <div style="text-align: center; margin: 30px 0;">
                <a href="{payment_link}" 
                   style="background-color: #10B981; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Pagar Agora
                </a>
            </div>
            """
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #4F46E5; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Fatura Gerada</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Uma nova fatura foi gerada:</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Número:</strong> {invoice_number}</p>
                    <p><strong>Valor:</strong> R$ {amount:,.2f}</p>
                    <p><strong>Vencimento:</strong> {due_date.strftime('%d/%m/%Y')}</p>
                </div>
                
                {payment_button}
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_invoice_expiring_soon(
        self,
        email: str,
        name: str,
        invoice_number: str,
        amount: float,
        due_date: datetime,
        days_until_due: int,
        payment_link: Optional[str] = None
    ) -> bool:
        """Send notification when invoice is close to expiration"""
        subject = f"Fatura Próxima do Vencimento - #{invoice_number}"
        
        payment_button = ""
        if payment_link:
            payment_button = f"""
            <div style="text-align: center; margin: 30px 0;">
                <a href="{payment_link}" 
                   style="background-color: #DC2626; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Pagar Agora
                </a>
            </div>
            """
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #F59E0B; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">⚠ Fatura Vencendo em {days_until_due} dias</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Sua fatura está próxima do vencimento:</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #F59E0B;">
                    <p><strong>Número:</strong> {invoice_number}</p>
                    <p><strong>Valor:</strong> R$ {amount:,.2f}</p>
                    <p><strong>Vencimento:</strong> {due_date.strftime('%d/%m/%Y')}</p>
                    <p style="color: #F59E0B;"><strong>Vence em {days_until_due} dias!</strong></p>
                </div>
                
                {payment_button}
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_payment_declined(
        self,
        email: str,
        name: str,
        invoice_number: str,
        amount: float,
        reason: Optional[str] = None
    ) -> bool:
        """Send notification when payment is declined"""
        subject = f"Pagamento Recusado - #{invoice_number}"
        
        reason_html = f"<p><strong>Motivo:</strong> {reason}</p>" if reason else ""
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #DC2626; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">❌ Pagamento Recusado</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Não conseguimos processar seu pagamento:</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Fatura:</strong> {invoice_number}</p>
                    <p><strong>Valor:</strong> R$ {amount:,.2f}</p>
                    {reason_html}
                </div>
                
                <p>Por favor, verifique seus dados de pagamento e tente novamente.</p>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_payment_confirmed(
        self,
        email: str,
        name: str,
        invoice_number: str,
        amount: float,
        payment_date: datetime,
        receipt_url: Optional[str] = None
    ) -> bool:
        """Send notification when payment is confirmed"""
        subject = f"Pagamento Confirmado - #{invoice_number}"
        
        receipt_button = ""
        if receipt_url:
            receipt_button = f"""
            <div style="text-align: center; margin: 30px 0;">
                <a href="{receipt_url}" 
                   style="background-color: #4F46E5; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Baixar Comprovante
                </a>
            </div>
            """
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #10B981; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">✓ Pagamento Confirmado</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Seu pagamento foi confirmado com sucesso!</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Fatura:</strong> {invoice_number}</p>
                    <p><strong>Valor:</strong> R$ {amount:,.2f}</p>
                    <p><strong>Data:</strong> {payment_date.strftime('%d/%m/%Y às %H:%M')}</p>
                </div>
                
                {receipt_button}
                
                <p style="color: #6B7280;">Obrigado pela sua preferência!</p>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_automatic_renewal(
        self,
        email: str,
        name: str,
        plan_name: str,
        amount: float,
        renewal_date: datetime,
        next_billing_date: datetime
    ) -> bool:
        """Send notification when subscription is automatically renewed"""
        subject = f"Renovação Automática - {plan_name}"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #10B981; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">✓ Renovação Automática</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Sua assinatura foi renovada automaticamente:</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Plano:</strong> {plan_name}</p>
                    <p><strong>Valor:</strong> R$ {amount:,.2f}</p>
                    <p><strong>Data de Renovação:</strong> {renewal_date.strftime('%d/%m/%Y')}</p>
                    <p><strong>Próxima Cobrança:</strong> {next_billing_date.strftime('%d/%m/%Y')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_plan_cancellation(
        self,
        email: str,
        name: str,
        plan_name: str,
        cancellation_date: datetime,
        access_until: datetime
    ) -> bool:
        """Send notification when plan is cancelled"""
        subject = f"Cancelamento de Plano - {plan_name}"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #6B7280; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Plano Cancelado</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Seu plano foi cancelado:</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Plano:</strong> {plan_name}</p>
                    <p><strong>Data de Cancelamento:</strong> {cancellation_date.strftime('%d/%m/%Y')}</p>
                    <p><strong>Acesso até:</strong> {access_until.strftime('%d/%m/%Y')}</p>
                </div>
                
                <p>Sentiremos sua falta! Para reativar, entre em contato conosco.</p>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_plan_upgrade_downgrade(
        self,
        email: str,
        name: str,
        old_plan: str,
        new_plan: str,
        change_date: datetime,
        is_upgrade: bool = True
    ) -> bool:
        """Send notification when plan is upgraded or downgraded"""
        action = "Upgrade" if is_upgrade else "Downgrade"
        subject = f"Alteração de Plano - {action}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #4F46E5; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Alteração de Plano</h1>
            </div>
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2>Olá, {name}!</h2>
                <p>Seu plano foi alterado:</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Plano Anterior:</strong> {old_plan}</p>
                    <p><strong>Novo Plano:</strong> {new_plan}</p>
                    <p><strong>Data da Alteração:</strong> {change_date.strftime('%d/%m/%Y')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )


# Global notification service instance
notification_service = NotificationService()
