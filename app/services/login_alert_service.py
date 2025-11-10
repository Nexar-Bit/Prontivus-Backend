"""
Login Alert Service
Handles sending login alerts to users when they log in
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


async def should_send_login_alert(
    user_id: int,
    db: AsyncSession
) -> bool:
    """
    Check if login alerts should be sent for a user
    
    Args:
        user_id: User ID
        db: Database session
    
    Returns:
        True if login alerts are enabled, False otherwise
    """
    from app.models import UserSettings
    
    try:
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        user_settings = result.scalar_one_or_none()
        
        if not user_settings or not user_settings.security:
            # Default to enabled
            return True
        
        return user_settings.security.get("loginAlerts", True)
    except Exception as e:
        logger.error(f"Error checking login alerts for user {user_id}: {str(e)}")
        # Default to enabled on error
        return True


async def send_login_alert(
    user_id: int,
    login_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """
    Send a login alert to the user
    
    Args:
        user_id: User ID
        login_ip: IP address of the login
        user_agent: User agent string
        db: Database session (optional, will create if not provided)
    
    Returns:
        True if alert was sent or skipped, False on error
    """
    from app.models import User
    from app.services.notification_dispatcher import send_system_update
    
    # Check if login alerts are enabled
    if db:
        enabled = await should_send_login_alert(user_id, db)
        if not enabled:
            logger.info(f"Login alerts disabled for user {user_id}, skipping alert")
            return True
    else:
        # If no db provided, we can't check settings, so default to enabled
        enabled = True
    
    if not enabled:
        return True
    
    # Get user information
    if not db:
        from database import get_async_session
        async for session in get_async_session():
            db = session
            break
    
    if not db:
        logger.error("Database session required for sending login alerts")
        return False
    
    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User {user_id} not found")
            return False
        
        # Format login details
        login_details = []
        if login_ip:
            login_details.append(f"IP: {login_ip}")
        if user_agent:
            # Extract browser/OS from user agent (simplified)
            browser = "Unknown"
            if "Chrome" in user_agent:
                browser = "Chrome"
            elif "Firefox" in user_agent:
                browser = "Firefox"
            elif "Safari" in user_agent:
                browser = "Safari"
            elif "Edge" in user_agent:
                browser = "Edge"
            login_details.append(f"Navegador: {browser}")
        
        login_time = datetime.now().strftime("%d/%m/%Y às %H:%M")
        login_details.append(f"Data/Hora: {login_time}")
        
        # Create alert message
        title = "Novo Login Detectado"
        message = f"Um novo login foi realizado na sua conta.\n\n"
        if login_details:
            message += "\n".join(login_details)
        message += "\n\nSe você não realizou este login, altere sua senha imediatamente."
        
        # Send notification through all enabled channels
        await send_system_update(
            user_id=user_id,
            update_title=title,
            update_message=message,
            action_url="/settings",
            db=db,
        )
        
        logger.info(f"Login alert sent to user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending login alert: {str(e)}")
        return False

