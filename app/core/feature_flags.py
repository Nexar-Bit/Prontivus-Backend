"""
Feature Flags System
Controls gradual rollout of new features
"""

import os
import hashlib
from typing import Dict, Optional


class FeatureFlags:
    """Feature flags for gradual rollout"""
    
    # Feature names
    PDF_GENERATION = "PDF_GENERATION"
    VOICE_TRANSCRIPTION = "VOICE_TRANSCRIPTION"
    AI_DIAGNOSIS = "AI_DIAGNOSIS"
    
    @staticmethod
    def is_enabled(feature: str) -> bool:
        """
        Check if a feature is enabled globally
        
        Args:
            feature: Feature name (e.g., "PDF_GENERATION")
        
        Returns:
            True if feature is enabled
        """
        env_var = f"ENABLE_{feature.upper()}"
        return os.getenv(env_var, "true").lower() == "true"
    
    @staticmethod
    def get_rollout_percentage(feature: str) -> int:
        """
        Get rollout percentage for a feature
        
        Args:
            feature: Feature name
        
        Returns:
            Rollout percentage (0-100)
        """
        env_var = f"{feature.upper()}_ROLLOUT"
        try:
            return int(os.getenv(env_var, "100"))
        except ValueError:
            return 100
    
    @staticmethod
    def should_enable_for_user(feature: str, user_id: int) -> bool:
        """
        Check if feature should be enabled for specific user
        Uses consistent hashing for stable rollout
        
        Args:
            feature: Feature name
            user_id: User ID
        
        Returns:
            True if feature should be enabled for this user
        """
        # Check if feature is globally enabled
        if not FeatureFlags.is_enabled(feature):
            return False
        
        # Get rollout percentage
        rollout = FeatureFlags.get_rollout_percentage(feature)
        if rollout >= 100:
            return True
        
        # Use consistent hashing based on user_id
        # This ensures same user always gets same result
        user_hash = int(hashlib.md5(f"{feature}_{user_id}".encode()).hexdigest(), 16) % 100
        return user_hash < rollout
    
    @staticmethod
    def get_all_features_status() -> Dict[str, Dict[str, any]]:
        """
        Get status of all features
        
        Returns:
            Dictionary with feature status
        """
        features = [
            FeatureFlags.PDF_GENERATION,
            FeatureFlags.VOICE_TRANSCRIPTION,
            FeatureFlags.AI_DIAGNOSIS,
        ]
        
        status = {}
        for feature in features:
            status[feature] = {
                "enabled": FeatureFlags.is_enabled(feature),
                "rollout_percentage": FeatureFlags.get_rollout_percentage(feature),
            }
        
        return status


# Convenience functions
def is_pdf_generation_enabled(user_id: Optional[int] = None) -> bool:
    """Check if PDF generation is enabled"""
    if user_id:
        return FeatureFlags.should_enable_for_user(FeatureFlags.PDF_GENERATION, user_id)
    return FeatureFlags.is_enabled(FeatureFlags.PDF_GENERATION)


def is_voice_transcription_enabled(user_id: Optional[int] = None) -> bool:
    """Check if voice transcription is enabled"""
    if user_id:
        return FeatureFlags.should_enable_for_user(FeatureFlags.VOICE_TRANSCRIPTION, user_id)
    return FeatureFlags.is_enabled(FeatureFlags.VOICE_TRANSCRIPTION)


def is_ai_diagnosis_enabled(user_id: Optional[int] = None) -> bool:
    """Check if AI diagnosis is enabled"""
    if user_id:
        return FeatureFlags.should_enable_for_user(FeatureFlags.AI_DIAGNOSIS, user_id)
    return FeatureFlags.is_enabled(FeatureFlags.AI_DIAGNOSIS)

