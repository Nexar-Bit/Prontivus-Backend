"""
Notification Dispatcher Service
Handles sending notifications through multiple channels (email, SMS, push)
while respecting user preferences for notification types
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def check_notification_type_enabled(
    user_id: int,
    notification_type: str,
    db
) -> bool:
    """
    Check if a specific notification type is enabled for a user
    
    Args:
        user_id: User ID to check
        notification_type: Type of notification ('appointmentReminders', 'systemUpdates', 'marketing')
        db: Database session
    
    Returns:
        True if notification type is enabled, False otherwise
    """
    from sqlalchemy import select
    from app.models import UserSettings
    
    try:
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        user_settings = result.scalar_one_or_none()
        
        if not user_settings:
            # Default values based on notification type
            defaults = {
                'appointmentReminders': True,
                'systemUpdates': True,
                'marketing': False,
            }
            return defaults.get(notification_type, False)
        
        notifications = user_settings.notifications or {}
        return notifications.get(notification_type, False)
        
    except Exception as e:
        logger.error(f"Error checking notification type {notification_type} for user {user_id}: {str(e)}")
        # Default values on error
        defaults = {
            'appointmentReminders': True,
            'systemUpdates': True,
            'marketing': False,
        }
        return defaults.get(notification_type, False)


async def send_notification(
    user_id: int,
    notification_title: str,
    notification_message: str,
    notification_type: str = "info",
    notification_category: str = "systemUpdates",  # 'appointmentReminders', 'systemUpdates', 'marketing'
    action_url: Optional[str] = None,
    db=None,
) -> Dict[str, Any]:
    """
    Send a notification through all enabled channels (email, SMS, push)
    while respecting user preferences for notification types
    
    Args:
        user_id: User ID
        notification_title: Title of the notification
        notification_message: Message content
        notification_type: Type of notification ('info', 'warning', 'error', 'success')
        notification_category: Category of notification ('appointmentReminders', 'systemUpdates', 'marketing')
        action_url: Optional URL for action button
        db: Database session (required)
    
    Returns:
        Dictionary with results for each channel:
        {
            'email': {'sent': bool, 'error': Optional[str]},
            'sms': {'sent': bool, 'error': Optional[str]},
            'push': {'sent': bool, 'count': int, 'error': Optional[str]}
        }
    """
    if not db:
        logger.error("Database session required for sending notifications")
        return {
            'email': {'sent': False, 'error': 'Database session required'},
            'sms': {'sent': False, 'error': 'Database session required'},
            'push': {'sent': False, 'count': 0, 'error': 'Database session required'},
        }
    
    results = {
        'email': {'sent': False, 'error': None},
        'sms': {'sent': False, 'error': None},
        'push': {'sent': False, 'count': 0, 'error': None},
    }
    
    # Check if this notification category is enabled
    category_enabled = await check_notification_type_enabled(user_id, notification_category, db)
    if not category_enabled:
        logger.info(f"Notification category '{notification_category}' disabled for user {user_id}, skipping all channels")
        return results
    
    # Get user information
    from sqlalchemy import select
    from app.models import User, UserSettings
    
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    
    if not user:
        logger.error(f"User {user_id} not found")
        return results
    
    # Get user settings for phone number
    settings_result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    user_settings = settings_result.scalar_one_or_none()
    user_phone = user_settings.phone if user_settings else None
    
    # Send email notification
    try:
        from app.services.email_service import send_notification_email_if_enabled
        email_sent = await send_notification_email_if_enabled(
            user_id=user_id,
            user_email=user.email,
            notification_title=notification_title,
            notification_message=notification_message,
            notification_type=notification_type,
            action_url=action_url,
            db=db,
        )
        results['email']['sent'] = email_sent
    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}")
        results['email']['error'] = str(e)
    
    # Send SMS notification
    if user_phone:
        try:
            from app.services.sms_service import send_notification_sms_if_enabled
            sms_sent = await send_notification_sms_if_enabled(
                user_id=user_id,
                user_phone=user_phone,
                notification_title=notification_title,
                notification_message=notification_message,
                db=db,
            )
            results['sms']['sent'] = sms_sent
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {str(e)}")
            results['sms']['error'] = str(e)
    else:
        results['sms']['error'] = 'Phone number not found'
    
    # Send push notification
    try:
        from app.services.push_service import send_push_notification_if_enabled
        push_count = await send_push_notification_if_enabled(
            user_id=user_id,
            title=notification_title,
            body=notification_message,
            icon="/favicon.png",
            data={'url': action_url} if action_url else None,
            tag=notification_category,
            db=db,
        )
        results['push']['sent'] = push_count > 0
        results['push']['count'] = push_count
    except Exception as e:
        logger.error(f"Failed to send push notification: {str(e)}")
        results['push']['error'] = str(e)
    
    return results


async def send_appointment_reminder(
    user_id: int,
    appointment_title: str,
    appointment_message: str,
    appointment_datetime: datetime,
    action_url: Optional[str] = None,
    db=None,
) -> Dict[str, Any]:
    """
    Send an appointment reminder notification
    
    Args:
        user_id: User ID
        appointment_title: Title of the appointment
        appointment_message: Message about the appointment
        appointment_datetime: Date and time of the appointment
        action_url: Optional URL to view appointment
        db: Database session
    
    Returns:
        Dictionary with notification results
    """
    title = f"Lembrete de Consulta: {appointment_title}"
    message = f"{appointment_message}\n\nData: {appointment_datetime.strftime('%d/%m/%Y às %H:%M')}"
    
    return await send_notification(
        user_id=user_id,
        notification_title=title,
        notification_message=message,
        notification_type="info",
        notification_category="appointmentReminders",
        action_url=action_url,
        db=db,
    )


async def send_system_update(
    user_id: int,
    update_title: str,
    update_message: str,
    action_url: Optional[str] = None,
    db=None,
) -> Dict[str, Any]:
    """
    Send a system update notification
    
    Args:
        user_id: User ID
        update_title: Title of the update
        update_message: Message about the update
        action_url: Optional URL to view update
        db: Database session
    
    Returns:
        Dictionary with notification results
    """
    return await send_notification(
        user_id=user_id,
        notification_title=update_title,
        notification_message=update_message,
        notification_type="info",
        notification_category="systemUpdates",
        action_url=action_url,
        db=db,
    )


async def send_marketing_notification(
    user_id: int,
    marketing_title: str,
    marketing_message: str,
    action_url: Optional[str] = None,
    db=None,
) -> Dict[str, Any]:
    """
    Send a marketing notification
    
    Args:
        user_id: User ID
        marketing_title: Title of the marketing message
        marketing_message: Marketing message content
        action_url: Optional URL for marketing action
        db: Database session
    
    Returns:
        Dictionary with notification results
    """
    return await send_notification(
        user_id=user_id,
        notification_title=marketing_title,
        notification_message=marketing_message,
        notification_type="info",
        notification_category="marketing",
        action_url=action_url,
        db=db,
    )

