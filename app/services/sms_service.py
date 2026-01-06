"""
SMS Service
Handles sending SMS notifications to users
Supports multiple providers (Twilio, AWS SNS, etc.)
"""
import os
import re
import asyncio
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SMSService:
    """Service for sending SMS notifications"""
    
    def __init__(self):
        # Load from environment variables first (highest priority), then config
        # Environment variables are loaded by python-dotenv in main.py before this module imports
        self.provider = os.getenv("SMS_PROVIDER", "twilio").lower()
        self.twilio_account_sid = os.getenv("SMS_TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.getenv("SMS_TWILIO_AUTH_TOKEN", "")
        self.twilio_from_number = os.getenv("SMS_TWILIO_FROM_NUMBER", "")
        
        # Fall back to config if environment variables are not set
        if not self.twilio_account_sid or not self.twilio_auth_token or not self.twilio_from_number:
            try:
                from config import settings
                self.provider = self.provider or getattr(settings, 'SMS_PROVIDER', 'twilio').lower()
                self.twilio_account_sid = self.twilio_account_sid or getattr(settings, 'SMS_TWILIO_ACCOUNT_SID', '')
                self.twilio_auth_token = self.twilio_auth_token or getattr(settings, 'SMS_TWILIO_AUTH_TOKEN', '')
                self.twilio_from_number = self.twilio_from_number or getattr(settings, 'SMS_TWILIO_FROM_NUMBER', '')
            except Exception as e:
                logger.debug(f"Could not load SMS settings from config: {e}")
        
        self.enabled = bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number)
        
        if self.enabled:
            logger.info(f"SMS service enabled with provider: {self.provider}")
            logger.debug(f"SMS FROM number: {self.twilio_from_number}")
        else:
            logger.warning("SMS service is disabled. SMS credentials not configured.")
    
    def is_enabled(self) -> bool:
        """Check if SMS service is enabled"""
        return self.enabled
    
    def normalize_phone_number(self, phone: str) -> str:
        """
        Normalize phone number to E.164 format
        Handles Brazilian phone numbers and international formats
        """
        if not phone:
            return ""
        
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Handle Brazilian phone numbers
        if digits.startswith('55'):
            # Already has country code
            if len(digits) == 13:  # 55 + 2 digit area code + 9 digits
                return f"+{digits}"
            elif len(digits) == 12:  # 55 + 2 digit area code + 8 digits (old format)
                return f"+{digits}"
        elif len(digits) == 11 and digits[0] == '0':
            # Remove leading 0 and add country code
            digits = '55' + digits[1:]
            return f"+{digits}"
        elif len(digits) == 10 or len(digits) == 11:
            # Brazilian number without country code
            if digits[0] in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                digits = '55' + digits
                return f"+{digits}"
        
        # If it doesn't start with +, add it
        if digits and not phone.startswith('+'):
            return f"+{digits}"
        
        return phone if phone.startswith('+') else f"+{digits}"
    
    async def send_sms(
        self,
        to_phone: str,
        message: str,
    ) -> bool:
        """
        Send an SMS to a phone number
        
        Args:
            to_phone: Recipient phone number (will be normalized)
            message: SMS message body (max 1600 characters for Twilio)
        
        Returns:
            True if SMS was sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning(f"SMS service disabled. Would send to {to_phone}: {message[:50]}...")
            return False
        
        if not to_phone:
            logger.error("No recipient phone number provided")
            return False
        
        if not message:
            logger.error("No message provided")
            return False
        
        # Normalize phone number
        normalized_phone = self.normalize_phone_number(to_phone)
        
        if not normalized_phone:
            logger.error(f"Invalid phone number format: {to_phone}")
            return False
        
        # Truncate message if too long (Twilio limit is 1600 characters)
        if len(message) > 1600:
            message = message[:1597] + "..."
            logger.warning(f"SMS message truncated to 1600 characters")
        
        try:
            if self.provider == "twilio":
                return await self._send_via_twilio(normalized_phone, message)
            else:
                logger.error(f"Unsupported SMS provider: {self.provider}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send SMS to {normalized_phone}: {str(e)}")
            return False
    
    async def _send_via_twilio(self, to_phone: str, message: str) -> bool:
        """Send SMS via Twilio (runs sync Twilio client in thread pool)"""
        try:
            from twilio.rest import Client
            
            def _send_sync():
                """Synchronous function to send SMS via Twilio"""
                client = Client(self.twilio_account_sid, self.twilio_auth_token)
                twilio_message = client.messages.create(
                    body=message,
                    from_=self.twilio_from_number,
                    to=to_phone
                )
                return twilio_message
            
            # Run synchronous Twilio client in thread pool to avoid blocking event loop
            twilio_message = await asyncio.to_thread(_send_sync)
            
            logger.info(f"SMS sent successfully to {to_phone} via Twilio. SID: {twilio_message.sid}")
            return True
            
        except ImportError:
            logger.error("twilio library not installed. Install with: pip install twilio")
            return False
        except Exception as e:
            logger.error(f"Twilio error sending SMS to {to_phone}: {str(e)}")
            return False
    
    async def send_notification_sms(
        self,
        to_phone: str,
        notification_title: str,
        notification_message: str,
    ) -> bool:
        """
        Send a notification SMS with a standardized format
        
        Args:
            to_phone: Recipient phone number
            notification_title: Title of the notification
            notification_message: Message content
        
        Returns:
            True if SMS was sent successfully, False otherwise
        """
        # Format SMS message (SMS-friendly, no HTML)
        sms_message = f"Prontivus: {notification_title}\n\n{notification_message}\n\n- Sistema Prontivus"
        
        return await self.send_sms(to_phone, sms_message)


# Global SMS service instance
sms_service = SMSService()


async def check_sms_notifications_enabled(user_id: int, db) -> bool:
    """
    Check if SMS notifications are enabled for a user
    
    Args:
        user_id: User ID to check
        db: Database session
    
    Returns:
        True if SMS notifications are enabled, False otherwise
    """
    from sqlalchemy import select
    from app.models import UserSettings
    
    try:
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        user_settings = result.scalar_one_or_none()
        
        if not user_settings:
            # Default to disabled if no settings exist (SMS costs money)
            return False
        
        notifications = user_settings.notifications or {}
        return notifications.get("sms", False)
        
    except Exception as e:
        logger.error(f"Error checking SMS notifications for user {user_id}: {str(e)}")
        # Default to disabled on error (SMS costs money)
        return False


async def send_notification_sms_if_enabled(
    user_id: int,
    user_phone: str,
    notification_title: str,
    notification_message: str,
    db=None,
) -> bool:
    """
    Send a notification SMS only if the user has SMS notifications enabled
    
    Args:
        user_id: User ID
        user_phone: User phone number
        notification_title: Title of the notification
        notification_message: Message content
        db: Database session (optional, will check settings if provided)
    
    Returns:
        True if SMS was sent or skipped due to disabled notifications, False on error
    """
    # Check if SMS notifications are enabled
    if db:
        enabled = await check_sms_notifications_enabled(user_id, db)
        if not enabled:
            logger.info(f"SMS notifications disabled for user {user_id}, skipping SMS")
            return True
    
    # Send SMS
    return await sms_service.send_notification_sms(
        to_phone=user_phone,
        notification_title=notification_title,
        notification_message=notification_message,
    )

