"""
Feedback API Endpoints
Handles user feedback and bug reports
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from datetime import datetime
import logging

from app.core.auth import get_current_user
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("")
async def submit_feedback(
    feature: str = Form(...),
    feature_name: str = Form(...),
    rating: int = Form(...),
    comment: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Submit feature feedback
    
    Args:
        feature: Feature identifier (pdf, voice, ai-diagnosis)
        feature_name: Display name of the feature
        rating: Rating from 1-5
        comment: Optional comment
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Success message
    """
    try:
        # Validate rating
        if not 1 <= rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
        # Log feedback (in production, store in database)
        logger.info(
            f"Feedback received - User: {current_user.email}, "
            f"Feature: {feature}, Rating: {rating}, Comment: {comment}"
        )
        
        # TODO: Store in database table
        # feedback = Feedback(
        #     user_id=current_user.id,
        #     clinic_id=current_user.clinic_id,
        #     feature=feature,
        #     feature_name=feature_name,
        #     rating=rating,
        #     comment=comment,
        #     created_at=datetime.utcnow()
        # )
        # db.add(feedback)
        # await db.commit()
        
        return {
            "success": True,
            "message": "Feedback recebido com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar feedback: {str(e)}")


@router.post("/bug-report")
async def submit_bug_report(
    title: str = Form(...),
    description: str = Form(...),
    steps: Optional[str] = Form(None),
    feature: Optional[str] = Form(None),
    browser: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    screenshots: List[UploadFile] = File([]),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Submit bug report with screenshots
    
    Args:
        title: Bug title
        description: Bug description
        steps: Steps to reproduce
        feature: Feature where bug occurred
        browser: Browser information
        url: URL where bug occurred
        screenshots: Screenshot files
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Success message
    """
    try:
        # Validate screenshots
        if len(screenshots) > 3:
            raise HTTPException(status_code=400, detail="Maximum 3 screenshots allowed")
        
        # Process screenshots
        screenshot_paths = []
        for screenshot in screenshots:
            if screenshot.content_type and not screenshot.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Only image files allowed")
            
            # TODO: Save to cloud storage or file system
            # For now, just log
            logger.info(f"Screenshot received: {screenshot.filename}, size: {screenshot.size}")
            screenshot_paths.append(screenshot.filename)
        
        # Log bug report
        logger.warning(
            f"Bug report received - User: {current_user.email}, "
            f"Title: {title}, Feature: {feature}, "
            f"Browser: {browser}, URL: {url}"
        )
        
        # TODO: Store in database table
        # bug_report = BugReport(
        #     user_id=current_user.id,
        #     clinic_id=current_user.clinic_id,
        #     title=title,
        #     description=description,
        #     steps=steps,
        #     feature=feature,
        #     browser=browser,
        #     url=url,
        #     screenshot_paths=screenshot_paths,
        #     created_at=datetime.utcnow()
        # )
        # db.add(bug_report)
        # await db.commit()
        
        return {
            "success": True,
            "message": "Relatório de bug enviado com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting bug report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar relatório: {str(e)}")


@router.get("/stats")
async def get_feedback_stats(
    feature: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get feedback statistics (admin only)
    
    Args:
        feature: Optional feature filter
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Feedback statistics
    """
    # TODO: Check if user is admin
    # if current_user.role not in ['admin', 'super_admin']:
    #     raise HTTPException(status_code=403, detail="Access denied")
    
    # TODO: Query database for stats
    return {
        "success": True,
        "stats": {
            "total_feedback": 0,
            "average_rating": 0,
            "feature_ratings": {}
        }
    }

