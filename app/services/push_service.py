"""
Push Notification Service
Handles sending web push notifications to users
"""
import json
import os
import base64
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import httpx

logger = logging.getLogger(__name__)


class PushService:
    """Service for sending web push notifications"""
    
    def __init__(self):
        # VAPID keys for web push (should be set in environment variables)
        # Try to get from config first, then fall back to environment
        try:
            from config import settings
            self.vapid_public_key = settings.VAPID_PUBLIC_KEY or os.getenv("VAPID_PUBLIC_KEY", "")
            self.vapid_private_key = settings.VAPID_PRIVATE_KEY or os.getenv("VAPID_PRIVATE_KEY", "")
            self.vapid_email = settings.VAPID_EMAIL or os.getenv("VAPID_EMAIL", "mailto:noreply@prontivus.com")
        except:
            self.vapid_public_key = os.getenv("VAPID_PUBLIC_KEY", "")
            self.vapid_private_key = os.getenv("VAPID_PRIVATE_KEY", "")
            self.vapid_email = os.getenv("VAPID_EMAIL", "mailto:noreply@prontivus.com")
        
        self.enabled = bool(self.vapid_public_key and self.vapid_private_key)
        
        if not self.enabled:
            logger.warning("Push notification service is disabled. VAPID keys not configured.")
    
    def is_enabled(self) -> bool:
        """Check if push service is enabled"""
        return self.enabled
    
    def get_vapid_public_key(self) -> str:
        """Get VAPID public key for frontend subscription"""
        return self.vapid_public_key
    
    async def send_push_notification(
        self,
        subscription: Dict[str, Any],
        title: str,
        body: str,
        icon: Optional[str] = None,
        badge: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        tag: Optional[str] = None,
        require_interaction: bool = False,
    ) -> bool:
        """
        Send a push notification to a subscription
        
        Args:
            subscription: Push subscription object with endpoint, keys, etc.
            title: Notification title
            body: Notification body
            icon: Optional icon URL
            badge: Optional badge URL
            data: Optional data payload
            tag: Optional notification tag (for replacing notifications)
            require_interaction: Whether notification requires user interaction
        
        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning(f"Push service disabled. Would send: {title}")
            return False
        
        try:
            from pywebpush import webpush, WebPushException
            
            # Prepare notification payload
            payload = {
                "title": title,
                "body": body,
                "icon": icon or "/favicon.png",
                "badge": badge or "/favicon.png",
                "tag": tag,
                "requireInteraction": require_interaction,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            if data:
                payload["data"] = data
            
            # Prepare subscription info
            subscription_info = {
                "endpoint": subscription["endpoint"],
                "keys": {
                    "p256dh": subscription["p256dh"],
                    "auth": subscription["auth"],
                }
            }
            
            # VAPID claims
            vapid_claims = {
                "sub": self.vapid_email,
            }
            
            # Decode private key if it's base64url encoded (from .env)
            # pywebpush accepts PEM format directly
            private_key = self.vapid_private_key
            try:
                # Try to decode if it's base64url encoded
                if not private_key.startswith('-----BEGIN'):
                    # It's base64url encoded, decode it
                    import base64
                    private_key = base64.urlsafe_b64decode(private_key + '==').decode('utf-8')
            except:
                # If decoding fails, assume it's already in PEM format
                pass
            
            # Send push notification
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=private_key,
                vapid_claims=vapid_claims,
            )
            
            logger.info(f"Push notification sent successfully: {title}")
            return True
            
        except ImportError:
            logger.error("pywebpush library not installed. Install with: pip install pywebpush")
            return False
        except Exception as e:
            logger.error(f"Failed to send push notification: {str(e)}")
            return False
    
    async def send_notification_to_user(
        self,
        user_id: int,
        title: str,
        body: str,
        icon: Optional[str] = None,
        badge: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        tag: Optional[str] = None,
        db=None,
    ) -> int:
        """
        Send push notification to all active subscriptions for a user
        
        Args:
            user_id: User ID
            title: Notification title
            body: Notification body
            icon: Optional icon URL
            badge: Optional badge URL
            data: Optional data payload
            tag: Optional notification tag
            db: Database session
        
        Returns:
            Number of notifications sent successfully
        """
        if not db:
            logger.error("Database session required to send push notifications")
            return 0
        
        from sqlalchemy import select
        from app.models.push_subscription import PushSubscription
        
        try:
            # Get all active subscriptions for user
            result = await db.execute(
                select(PushSubscription).where(
                    PushSubscription.user_id == user_id,
                    PushSubscription.is_active == True
                )
            )
            subscriptions = result.scalars().all()
            
            if not subscriptions:
                logger.info(f"No active push subscriptions found for user {user_id}")
                return 0
            
            # Send to all subscriptions
            success_count = 0
            for subscription in subscriptions:
                try:
                    subscription_dict = {
                        "endpoint": subscription.endpoint,
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    }
                    
                    success = await self.send_push_notification(
                        subscription=subscription_dict,
                        title=title,
                        body=body,
                        icon=icon,
                        badge=badge,
                        data=data,
                        tag=tag,
                    )
                    
                    if success:
                        success_count += 1
                    else:
                        # Mark subscription as inactive if it fails
                        subscription.is_active = False
                        await db.commit()
                        
                except Exception as e:
                    logger.error(f"Failed to send push to subscription {subscription.id}: {str(e)}")
                    # Mark subscription as inactive on error
                    subscription.is_active = False
                    await db.commit()
            
            return success_count
            
        except Exception as e:
            logger.error(f"Error sending push notifications to user {user_id}: {str(e)}")
            return 0


# Global push service instance
push_service = PushService()


async def check_push_notifications_enabled(user_id: int, db) -> bool:
    """
    Check if push notifications are enabled for a user
    
    Args:
        user_id: User ID to check
        db: Database session
    
    Returns:
        True if push notifications are enabled, False otherwise
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
        return notifications.get("push", True)
        
    except Exception as e:
        logger.error(f"Error checking push notifications for user {user_id}: {str(e)}")
        # Default to enabled on error
        return True


async def send_push_notification_if_enabled(
    user_id: int,
    title: str,
    body: str,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    tag: Optional[str] = None,
    db=None,
) -> int:
    """
    Send a push notification only if the user has push notifications enabled
    
    Args:
        user_id: User ID
        title: Notification title
        body: Notification body
        icon: Optional icon URL
        badge: Optional badge URL
        data: Optional data payload
        tag: Optional notification tag
        db: Database session (required)
    
    Returns:
        Number of notifications sent successfully
    """
    if not db:
        logger.error("Database session required")
        return 0
    
    # Check if push notifications are enabled
    enabled = await check_push_notifications_enabled(user_id, db)
    if not enabled:
        logger.info(f"Push notifications disabled for user {user_id}, skipping push")
        return 0
    
    # Send push notification
    return await push_service.send_notification_to_user(
        user_id=user_id,
        title=title,
        body=body,
        icon=icon,
        badge=badge,
        data=data,
        tag=tag,
        db=db,
    )

