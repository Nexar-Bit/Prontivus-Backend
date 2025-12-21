"""
Email Service
Handles sending email notifications to  users
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications"""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtpout.secureserver.net")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_from_email = os.getenv("SMTP_FROM_EMAIL", "suporte@prontivus.com")
        self.enabled = bool(self.smtp_user and self.smtp_password)
        
        if not self.enabled:
            logger.warning("Email service is disabled. SMTP credentials not configured.")
    
    def is_enabled(self) -> bool:
        """Check if email service is enabled"""
        return self.enabled
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """
        Send an email to a recipient
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning(f"Email service disabled. Would send to {to_email}: {subject}")
            return False
        
        if not to_email:
            logger.error("No recipient email provided")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_from_email
            msg['To'] = to_email
            
            # Add text and HTML parts
            if text_body:
                text_part = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(text_part)
            
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Send email
            # Port 465 uses SSL, port 587 uses TLS
            import ssl
            
            # Create SSL context optimized for GoDaddy/SecureServer
            context = ssl.create_default_context()
            # GoDaddy requires less strict verification
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            # Support a wider range of TLS versions for compatibility
            context.minimum_version = ssl.TLSVersion.MINIMUM_SUPPORTED
            context.maximum_version = ssl.TLSVersion.MAXIMUM_SUPPORTED
            
            # Use longer timeout for GoDaddy servers (they can be slow)
            timeout = 120  # Increased from 60 to 120 seconds
            
            # Port 465 and 3535 use SSL, others use TLS
            if self.smtp_port == 465 or self.smtp_port == 3535:
                # Use SSL for ports 465 and 3535 (GoDaddy SSL ports)
                # For GoDaddy, we need to connect without SSL first, then upgrade
                logger.info(f"Connecting to {self.smtp_host}:{self.smtp_port} using SSL...")
                try:
                    # Try direct SSL connection first
                    with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context, timeout=timeout) as server:
                        server.login(self.smtp_user, self.smtp_password)
                        server.send_message(msg)
                except (ssl.SSLError, OSError) as ssl_error:
                    # If SSL fails, try connecting without SSL first, then upgrading
                    logger.warning(f"Direct SSL connection failed: {ssl_error}. Trying alternative method...")
                    with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=timeout) as server:
                        server.starttls(context=context)
                        server.login(self.smtp_user, self.smtp_password)
                        server.send_message(msg)
            else:
                # Use TLS for port 587 and others (25, 80, etc.)
                logger.info(f"Connecting to {self.smtp_host}:{self.smtp_port} using TLS...")
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=timeout) as server:
                    server.ehlo()  # Identify client to server
                    server.starttls(context=context)  # Upgrade to TLS
                    server.ehlo()  # Re-identify after TLS upgrade
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    async def send_notification_email(
        self,
        to_email: str,
        notification_title: str,
        notification_message: str,
        notification_type: str = "info",
        action_url: Optional[str] = None,
    ) -> bool:
        """
        Send a notification email with a standardized template
        
        Args:
            to_email: Recipient email address
            notification_title: Title of the notification
            notification_message: Message content
            notification_type: Type of notification (info, warning, error, success)
            action_url: Optional URL for action button
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        # Determine color based on notification type
        color_map = {
            "info": "#3b82f6",  # Blue
            "warning": "#f59e0b",  # Amber
            "error": "#ef4444",  # Red
            "success": "#10b981",  # Green
            "appointment": "#5b9eff",  # Soft blue
        }
        color = color_map.get(notification_type, "#3b82f6")
        
        # Generate HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background-color: #ffffff;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .header {{
                    border-bottom: 3px solid {color};
                    padding-bottom: 20px;
                    margin-bottom: 20px;
                }}
                .logo {{
                    color: {color};
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .title {{
                    font-size: 20px;
                    font-weight: 600;
                    color: #1f2937;
                    margin-bottom: 10px;
                }}
                .message {{
                    font-size: 16px;
                    color: #4b5563;
                    margin-bottom: 20px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: {color};
                    color: #ffffff;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 500;
                    margin-top: 10px;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    font-size: 12px;
                    color: #6b7280;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">Prontivus</div>
                    <div class="title">{notification_title}</div>
                </div>
                <div class="message">
                    {notification_message}
                </div>
                {f'<a href="{action_url}" class="button">Ver Detalhes</a>' if action_url else ''}
                <div class="footer">
                    <p>Este é um email automático do sistema Prontivus.</p>
                    <p>Se você não esperava receber este email, pode ignorá-lo com segurança.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Generate plain text version
        text_body = f"""
Prontivus - {notification_title}

{notification_message}

{f'Acesse: {action_url}' if action_url else ''}

---
Este é um email automático do sistema Prontivus.
Se você não esperava receber este email, pode ignorá-lo com segurança.
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Prontivus: {notification_title}",
            html_body=html_body,
            text_body=text_body,
        )


# Global email service instance
email_service = EmailService()


async def check_email_notifications_enabled(user_id: int, db) -> bool:
    """
    Check if email notifications are enabled for a user
    
    Args:
        user_id: User ID to check
        db: Database session
    
    Returns:
        True if email notifications are enabled, False otherwise
    """
    from sqlalchemy import select
    from app.models import UserSettings
    
    try:
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        user_settings = result.scalar_one_or_none()
        
        if not user_settings:
            # Default to enabled if no settings exist
            return True
        
        notifications = user_settings.notifications or {}
        return notifications.get("email", True)
        
    except Exception as e:
        logger.error(f"Error checking email notifications for user {user_id}: {str(e)}")
        # Default to enabled on error
        return True


async def send_notification_email_if_enabled(
    user_id: int,
    user_email: str,
    notification_title: str,
    notification_message: str,
    notification_type: str = "info",
    action_url: Optional[str] = None,
    db=None,
) -> bool:
    """
    Send a notification email only if the user has email notifications enabled
    
    Args:
        user_id: User ID
        user_email: User email address
        notification_title: Title of the notification
        notification_message: Message content
        notification_type: Type of notification
        action_url: Optional URL for action button
        db: Database session (optional, will check settings if provided)
    
    Returns:
        True if email was sent or skipped due to disabled notifications, False on error
    """
    # Check if email notifications are enabled
    if db:
        enabled = await check_email_notifications_enabled(user_id, db)
        if not enabled:
            logger.info(f"Email notifications disabled for user {user_id}, skipping email")
            return True
    
    # Send email
    return await email_service.send_notification_email(
        to_email=user_email,
        notification_title=notification_title,
        notification_message=notification_message,
        notification_type=notification_type,
        action_url=action_url,
    )

