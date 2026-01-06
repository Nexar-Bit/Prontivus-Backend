"""
Enhanced security configuration and utilities
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from config import settings

# Password hashing context
# Configure bcrypt to avoid wrap bug detection issues
# The issue occurs when passlib tries to detect wrap bug during initialization
# We'll use bcrypt directly for verification to bypass this issue
# But keep passlib for hashing (which doesn't trigger the wrap bug detection)
try:
    # Initialize passlib for hashing (hashing doesn't trigger wrap bug detection)
    pwd_context = CryptContext(
        schemes=["bcrypt"],
        deprecated="auto",
        bcrypt__rounds=12
    )
except Exception as e:
    # If initialization fails, use default configuration
    import logging
    logging.warning(f"Bcrypt initialization warning: {e}")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate limiting storage (in production, use Redis)
login_attempts: Dict[str, Dict[str, Any]] = {}

# Security constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
PASSWORD_RESET_EXPIRE_HOURS = 1


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    # Bcrypt has a 72-byte limit, truncate if necessary
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
            password = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    import bcrypt
    
    try:
        # Bcrypt has a 72-byte limit, truncate if necessary before verification
        if isinstance(plain_password, str):
            password_bytes = plain_password.encode('utf-8')
            if len(password_bytes) > 72:
                # Truncate to 72 bytes, but try to preserve as much as possible
                password_bytes = password_bytes[:72]
                # Remove any incomplete UTF-8 sequences at the end
                while password_bytes and (password_bytes[-1] & 0xC0) == 0x80:
                    password_bytes = password_bytes[:-1]
                plain_password = password_bytes.decode('utf-8', errors='ignore')
        
        # Use bcrypt directly to avoid passlib initialization issues
        # This bypasses the wrap bug detection that happens during passlib initialization
        if isinstance(hashed_password, str):
            hashed_bytes = hashed_password.encode('utf-8')
        else:
            hashed_bytes = hashed_password
            
        password_bytes = plain_password.encode('utf-8')
        
        # Use bcrypt.checkpw directly
        return bcrypt.checkpw(password_bytes, hashed_bytes)
        
    except (ValueError, Exception) as e:
        # Fallback to passlib if direct bcrypt fails
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Convert datetime to Unix timestamp for JWT standard compliance
    # This ensures proper handling even if system time changes
    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
        "jti": generate_secure_token(16)  # JWT ID for token tracking
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Convert datetime to Unix timestamp for JWT standard compliance
    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "refresh",
        "jti": generate_secure_token(16)
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token
    
    Handles timezone changes and clock skew by manually checking expiration
    with a 60-second tolerance. This ensures tokens remain valid even if
    system time changes or there's clock drift between client and server.
    """
    try:
        # Decode token without automatic expiration check
        # We'll manually check expiration with leeway to handle timezone changes
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={
                "verify_signature": True,
                "verify_exp": False,  # We'll check manually with leeway
                "verify_iat": False,  # We'll check manually with leeway
                "verify_nbf": False,  # Not using nbf claim
                "require_exp": False,
                "require_iat": False,
            }
        )
        
        # Manual expiration check with 60 seconds leeway for timezone changes
        CLOCK_SKEW_SECONDS = 60
        now = datetime.utcnow()
        current_timestamp = int(now.timestamp())
        
        # Check expiration with leeway
        exp = payload.get("exp")
        if exp is not None:
            # Token is expired if current time is more than leeway seconds past expiration
            if current_timestamp > (exp + CLOCK_SKEW_SECONDS):
                raise JWTError("Token has expired")
        
        # Check issued at time with leeway (prevent tokens from future)
        iat = payload.get("iat")
        if iat is not None:
            # Token is invalid if issued more than leeway seconds in the future
            if (iat - CLOCK_SKEW_SECONDS) > current_timestamp:
                raise JWTError("Token issued in the future")
        
        # Check token type (custom claim)
        if payload.get("type") not in ["access", "refresh"]:
            raise JWTError("Invalid token type")
        
        return payload
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def check_login_attempts(identifier: str) -> bool:
    """Check if login attempts are within limits"""
    now = datetime.utcnow()
    
    if identifier not in login_attempts:
        return True
    
    attempts = login_attempts[identifier]
    
    # Check if locked out
    if attempts.get("locked_until") and now < attempts["locked_until"]:
        return False
    
    # Reset if lockout period has passed
    if attempts.get("locked_until") and now >= attempts["locked_until"]:
        login_attempts[identifier] = {"count": 0, "last_attempt": None, "locked_until": None}
        return True
    
    # Check attempt count
    return attempts.get("count", 0) < MAX_LOGIN_ATTEMPTS


def record_login_attempt(identifier: str, success: bool) -> None:
    """Record a login attempt"""
    now = datetime.utcnow()
    
    if identifier not in login_attempts:
        login_attempts[identifier] = {"count": 0, "last_attempt": None, "locked_until": None}
    
    attempts = login_attempts[identifier]
    
    if success:
        # Reset on successful login
        login_attempts[identifier] = {"count": 0, "last_attempt": None, "locked_until": None}
    else:
        # Increment failed attempts
        attempts["count"] = attempts.get("count", 0) + 1
        attempts["last_attempt"] = now
        
        # Lock account if max attempts reached
        if attempts["count"] >= MAX_LOGIN_ATTEMPTS:
            attempts["locked_until"] = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)


def create_password_reset_token(email: str) -> str:
    """Create a password reset token"""
    now = datetime.utcnow()
    expire = now + timedelta(hours=PASSWORD_RESET_EXPIRE_HOURS)
    
    data = {
        "email": email,
        "type": "password_reset",
        "exp": int(expire.timestamp())  # Convert to Unix timestamp
    }
    
    return jwt.encode(
        data,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def verify_password_reset_token(token: str) -> str:
    """Verify a password reset token and return email"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        if payload.get("type") != "password_reset":
            raise JWTError("Invalid token type")
        
        return payload.get("email")
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token"
        )


def get_password_strength_score(password: str) -> int:
    """Calculate password strength score (0-100)"""
    score = 0
    
    # Length bonus
    if len(password) >= 8:
        score += 20
    if len(password) >= 12:
        score += 10
    if len(password) >= 16:
        score += 10
    
    # Character variety
    if any(c.islower() for c in password):
        score += 10
    if any(c.isupper() for c in password):
        score += 10
    if any(c.isdigit() for c in password):
        score += 10
    if any(c in "!@#$%^&*(),.?\":{}|<>" for c in password):
        score += 20
    
    # Pattern penalties
    if password.lower() in ["password", "123456", "qwerty"]:
        score = 0
    
    return min(score, 100)
