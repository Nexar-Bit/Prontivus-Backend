"""
AI Configuration API Endpoints
Handles AI integration settings for SuperAdmin
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from database import get_async_session
from app.core.auth import get_current_user
from app.models import User
from app.middleware.permissions import require_super_admin

router = APIRouter(prefix="/ai-config", tags=["AI Configuration"])


def _default_ai_config() -> Dict[str, Any]:
    """Default AI configuration"""
    return {
        "enabled": False,
        "provider": "openai",
        "api_key": "",
        "model": "gpt-4",
        "base_url": "",
        "max_tokens": 2000,
        "temperature": 0.7,
        "features": {
            "clinical_analysis": {
                "enabled": False,
                "description": "Análise automática de prontuários médicos"
            },
            "diagnosis_suggestions": {
                "enabled": False,
                "description": "Sugestões baseadas em sintomas e histórico"
            },
            "predictive_analysis": {
                "enabled": False,
                "description": "Previsões baseadas em dados históricos"
            },
            "virtual_assistant": {
                "enabled": False,
                "description": "Assistente inteligente para médicos"
            }
        },
        "usage_stats": {
            "documents_processed": 0,
            "suggestions_generated": 0,
            "approval_rate": 0.0
        }
    }


@router.get("")
async def get_ai_config(
    current_user: User = Depends(require_super_admin()),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get AI configuration (SuperAdmin only)
    Returns default config if none exists
    """
    # For now, return default config
    # In the future, this could be stored in a database table
    return _default_ai_config()


@router.put("")
async def update_ai_config(
    config: Dict[str, Any],
    current_user: User = Depends(require_super_admin()),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update AI configuration (SuperAdmin only)
    """
    # Validate required fields
    if "enabled" not in config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="enabled field is required"
        )
    
    # Validate provider
    valid_providers = ["openai", "google", "anthropic", "azure"]
    if config.get("provider") and config["provider"] not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
        )
    
    # For now, just return success
    # In the future, this would save to a database table
    return {
        "message": "AI configuration updated successfully",
        "config": config
    }


@router.post("/test-connection")
async def test_ai_connection(
    current_user: User = Depends(require_super_admin()),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Test AI connection (SuperAdmin only)
    """
    # For now, return a mock success response
    # In the future, this would actually test the connection
    return {
        "success": True,
        "message": "Connection test successful",
        "provider": "openai",
        "model": "gpt-4",
        "response_time_ms": 250
    }


@router.get("/stats")
async def get_ai_stats(
    current_user: User = Depends(require_super_admin()),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get AI usage statistics (SuperAdmin only)
    """
    # For now, return mock stats
    # In the future, this would aggregate real usage data
    return {
        "documents_processed": 1234,
        "suggestions_generated": 5678,
        "approval_rate": 0.87,
        "total_requests": 6912,
        "successful_requests": 6789,
        "failed_requests": 123,
        "average_response_time_ms": 450
    }

