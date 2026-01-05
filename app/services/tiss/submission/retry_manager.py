"""
Retry Manager Service
Manages retry logic for TISS batch submissions
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.tiss.batch import TISSBatch

logger = logging.getLogger(__name__)


class RetryManager:
    """Manages retry logic for failed submissions"""
    
    # Exponential backoff: 1min, 5min, 15min, 1h, 4h
    RETRY_DELAYS = [60, 300, 900, 3600, 14400]  # seconds
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def should_retry(self, batch_id: int) -> bool:
        """Check if batch should be retried"""
        query = select(TISSBatch).where(TISSBatch.id == batch_id)
        result = await self.db.execute(query)
        batch = result.scalar_one_or_none()
        
        if not batch:
            return False
        
        if batch.retry_count >= batch.max_retries:
            return False
        
        if batch.submission_status == 'success':
            return False
        
        return True
    
    async def get_next_retry_time(self, batch_id: int) -> Optional[datetime]:
        """Get next retry time for batch"""
        query = select(TISSBatch).where(TISSBatch.id == batch_id)
        result = await self.db.execute(query)
        batch = result.scalar_one_or_none()
        
        if not batch or not await self.should_retry(batch_id):
            return None
        
        if batch.last_retry_at:
            delay_seconds = self.RETRY_DELAYS[min(batch.retry_count, len(self.RETRY_DELAYS) - 1)]
            return batch.last_retry_at + timedelta(seconds=delay_seconds)
        
        return datetime.now()
    
    async def increment_retry(self, batch_id: int):
        """Increment retry count and update last retry time"""
        query = select(TISSBatch).where(TISSBatch.id == batch_id)
        result = await self.db.execute(query)
        batch = result.scalar_one_or_none()
        
        if batch:
            batch.retry_count += 1
            batch.last_retry_at = datetime.now()
            await self.db.commit()

