"""
Two Factor Authentication Service
Handles 2FA setup, verification, and management
"""
import pyotp
import qrcode
import io
import base64
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


class TwoFactorService:
    """Service for managing two-factor authentication"""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code_uri(secret: str, email: str, issuer: str = "Prontivus") -> str:
        """Generate QR code URI for authenticator app"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=email,
            issuer_name=issuer
        )
    
    @staticmethod
    def generate_qr_code_image(uri: str) -> str:
        """Generate QR code image as base64 string"""
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"
        except Exception as e:
            logger.error(f"Error generating QR code: {str(e)}")
            return ""
    
    @staticmethod
    def verify_code(secret: str, code: str) -> bool:
        """Verify a TOTP code"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=1)  # Allow 1 time step window
        except Exception as e:
            logger.error(f"Error verifying TOTP code: {str(e)}")
            return False
    
    @staticmethod
    async def get_user_2fa_secret(
        user_id: int,
        db: AsyncSession
    ) -> Optional[str]:
        """Get user's 2FA secret from settings"""
        from app.models import UserSettings
        
        try:
            result = await db.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            user_settings = result.scalar_one_or_none()
            
            if not user_settings or not user_settings.security:
                return None
            
            # 2FA secret should be stored in security settings
            # For security, we only return it during setup, not after
            return user_settings.security.get("twoFactorSecret")
        except Exception as e:
            logger.error(f"Error getting 2FA secret for user {user_id}: {str(e)}")
            return None
    
    @staticmethod
    async def setup_2fa(
        user_id: int,
        user_email: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Setup 2FA for a user"""
        from app.models import UserSettings
        
        # Generate new secret
        secret = TwoFactorService.generate_secret()
        
        # Generate QR code URI
        qr_uri = TwoFactorService.generate_qr_code_uri(secret, user_email)
        
        # Generate QR code image
        qr_image = TwoFactorService.generate_qr_code_image(qr_uri)
        
        # Get or create user settings
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        user_settings = result.scalar_one_or_none()
        
        if not user_settings:
            from app.api.endpoints.user_settings import get_default_settings
            defaults = get_default_settings()
            user_settings = UserSettings(
                user_id=user_id,
                notifications=defaults["notifications"],
                privacy=defaults["privacy"],
                appearance=defaults["appearance"],
                security=defaults["security"],
            )
            db.add(user_settings)
        
        # Store secret temporarily (will be confirmed after verification)
        if not user_settings.security:
            user_settings.security = {}
        user_settings.security["twoFactorSecret"] = secret
        user_settings.security["twoFactorEnabled"] = False  # Not enabled until verified
        
        await db.commit()
        
        return {
            "secret": secret,
            "qr_uri": qr_uri,
            "qr_image": qr_image,
        }
    
    @staticmethod
    async def verify_and_enable_2fa(
        user_id: int,
        code: str,
        db: AsyncSession
    ) -> bool:
        """Verify 2FA code and enable 2FA"""
        from app.models import UserSettings
        
        try:
            result = await db.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            user_settings = result.scalar_one_or_none()
            
            if not user_settings or not user_settings.security:
                return False
            
            secret = user_settings.security.get("twoFactorSecret")
            if not secret:
                return False
            
            # Verify code
            if not TwoFactorService.verify_code(secret, code):
                return False
            
            # Enable 2FA
            user_settings.security["twoFactorEnabled"] = True
            user_settings.security["twoFactorAuth"] = True  # Also update the main setting
            
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error verifying and enabling 2FA: {str(e)}")
            await db.rollback()
            return False
    
    @staticmethod
    async def disable_2fa(
        user_id: int,
        db: AsyncSession
    ) -> bool:
        """Disable 2FA for a user"""
        from app.models import UserSettings
        
        try:
            result = await db.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            user_settings = result.scalar_one_or_none()
            
            if not user_settings:
                return False
            
            if not user_settings.security:
                user_settings.security = {}
            
            # Remove secret and disable 2FA
            user_settings.security.pop("twoFactorSecret", None)
            user_settings.security["twoFactorEnabled"] = False
            user_settings.security["twoFactorAuth"] = False
            
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error disabling 2FA: {str(e)}")
            await db.rollback()
            return False
    
    @staticmethod
    async def is_2fa_enabled(
        user_id: int,
        db: AsyncSession
    ) -> bool:
        """Check if 2FA is enabled for a user"""
        from app.models import UserSettings
        
        try:
            result = await db.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            user_settings = result.scalar_one_or_none()
            
            if not user_settings or not user_settings.security:
                return False
            
            return user_settings.security.get("twoFactorEnabled", False) or \
                   user_settings.security.get("twoFactorAuth", False)
        except Exception as e:
            logger.error(f"Error checking 2FA status: {str(e)}")
            return False


# Global service instance
two_factor_service = TwoFactorService()

