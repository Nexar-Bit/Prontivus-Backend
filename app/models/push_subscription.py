"""
Push Subscription Model
Stores web push notification subscriptions for users
"""
from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class PushSubscription(Base):
    """
    Push Subscription Model
    Stores web push notification subscriptions for users
    """
    __tablename__ = "push_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Push subscription endpoint and keys (from Push API)
    endpoint = Column(String(500), nullable=False)
    p256dh = Column(String(200), nullable=False)  # Public key
    auth = Column(String(100), nullable=False)  # Auth secret
    
    # Additional subscription metadata
    user_agent = Column(String(500), nullable=True)
    device_info = Column(JSON, nullable=True)  # Store device info like OS, browser, etc.
    
    # Subscription status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="push_subscriptions")
    
    def __repr__(self):
        return f"<PushSubscription(id={self.id}, user_id={self.user_id}, endpoint={self.endpoint[:50]}...)>"

