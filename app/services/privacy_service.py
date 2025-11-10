"""
Privacy Service
Handles privacy-related functionality based on user privacy settings
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


async def get_user_privacy_settings(
    user_id: int,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Get user's privacy settings
    
    Args:
        user_id: User ID
        db: Database session
    
    Returns:
        Dictionary with privacy settings
    """
    from app.models import UserSettings
    
    try:
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        user_settings = result.scalar_one_or_none()
        
        if not user_settings or not user_settings.privacy:
            # Return defaults
            return {
                "profileVisibility": "contacts",
                "showOnlineStatus": True,
                "allowDirectMessages": True,
                "dataSharing": False,
            }
        
        return user_settings.privacy
        
    except Exception as e:
        logger.error(f"Error getting privacy settings for user {user_id}: {str(e)}")
        # Return defaults on error
        return {
            "profileVisibility": "contacts",
            "showOnlineStatus": True,
            "allowDirectMessages": True,
            "dataSharing": False,
        }


async def can_view_user_profile(
    viewer_user_id: int,
    target_user_id: int,
    db: AsyncSession
) -> bool:
    """
    Check if a user can view another user's profile based on privacy settings
    
    Args:
        viewer_user_id: ID of the user trying to view
        target_user_id: ID of the user whose profile is being viewed
        db: Database session
    
    Returns:
        True if viewer can see the profile, False otherwise
    """
    if viewer_user_id == target_user_id:
        # Users can always see their own profile
        return True
    
    privacy_settings = await get_user_privacy_settings(target_user_id, db)
    visibility = privacy_settings.get("profileVisibility", "contacts")
    
    if visibility == "public":
        return True
    elif visibility == "private":
        return False
    elif visibility == "contacts":
        # Check if users are contacts (simplified - would need contact system)
        # For now, return True if they're in the same clinic
        from app.models import User
        viewer_result = await db.execute(
            select(User).where(User.id == viewer_user_id)
        )
        target_result = await db.execute(
            select(User).where(User.id == target_user_id)
        )
        viewer = viewer_result.scalar_one_or_none()
        target = target_result.scalar_one_or_none()
        
        if viewer and target:
            return viewer.clinic_id == target.clinic_id
        
        return False
    
    return False


async def can_send_direct_message(
    sender_user_id: int,
    recipient_user_id: int,
    db: AsyncSession
) -> bool:
    """
    Check if a user can send a direct message to another user
    
    Args:
        sender_user_id: ID of the user sending the message
        recipient_user_id: ID of the user receiving the message
        db: Database session
    
    Returns:
        True if message can be sent, False otherwise
    """
    if sender_user_id == recipient_user_id:
        # Users can always message themselves (for notes, etc.)
        return True
    
    privacy_settings = await get_user_privacy_settings(recipient_user_id, db)
    allow_direct_messages = privacy_settings.get("allowDirectMessages", True)
    
    return allow_direct_messages


async def can_share_data(
    user_id: int,
    db: AsyncSession
) -> bool:
    """
    Check if user has allowed data sharing
    
    Args:
        user_id: User ID
        db: Database session
    
    Returns:
        True if data sharing is allowed, False otherwise
    """
    privacy_settings = await get_user_privacy_settings(user_id, db)
    data_sharing = privacy_settings.get("dataSharing", False)
    
    return data_sharing


async def should_show_online_status(
    user_id: int,
    db: AsyncSession
) -> bool:
    """
    Check if user's online status should be shown
    
    Args:
        user_id: User ID
        db: Database session
    
    Returns:
        True if online status should be shown, False otherwise
    """
    privacy_settings = await get_user_privacy_settings(user_id, db)
    show_online_status = privacy_settings.get("showOnlineStatus", True)
    
    return show_online_status


async def get_user_online_status(
    user_id: int,
    viewer_user_id: int,
    db: AsyncSession
) -> Optional[bool]:
    """
    Get user's online status if it should be visible to the viewer
    
    Args:
        user_id: ID of the user whose status is being checked
        viewer_user_id: ID of the user viewing the status
        db: Database session
    
    Returns:
        True if online, False if offline, None if status should be hidden
    """
    # Check if user wants to show online status
    should_show = await should_show_online_status(user_id, db)
    if not should_show:
        return None
    
    # Check if viewer can see the profile
    can_view = await can_view_user_profile(viewer_user_id, user_id, db)
    if not can_view:
        return None
    
    # TODO: Implement actual online status tracking
    # For now, return None (status not tracked)
    return None

