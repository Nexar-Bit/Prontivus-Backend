"""
TISS Versioning Service
Manages TISS standard versions and XSD files
"""

import os
import logging
from typing import Optional, Dict, List
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from app.models.tiss.version import TISSVersion
from database import get_async_session

logger = logging.getLogger(__name__)


class TISSVersioningService:
    """Service for managing TISS versions"""
    
    # Current TISS version (as of 2024/2025)
    CURRENT_TISS_VERSION = "3.05.02"
    
    # Supported TISS versions
    SUPPORTED_VERSIONS = [
        "3.05.02",  # Current version
        "3.03.00",  # Previous version (still supported)
    ]
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.xsd_base_path = Path("backend/app/services/tiss/xsd")
    
    async def get_current_version(self) -> str:
        """Get current active TISS version"""
        return self.CURRENT_TISS_VERSION
    
    async def get_supported_versions(self) -> List[str]:
        """Get list of supported TISS versions"""
        return self.SUPPORTED_VERSIONS
    
    async def get_version_info(self, version: str) -> Optional[Dict]:
        """Get information about a specific TISS version"""
        query = select(TISSVersion).where(TISSVersion.version == version)
        result = await self.db.execute(query)
        version_obj = result.scalar_one_or_none()
        
        if not version_obj:
            return None
        
        return {
            "version": version_obj.version,
            "is_active": version_obj.is_active,
            "release_date": version_obj.release_date.isoformat() if version_obj.release_date else None,
            "end_of_life_date": version_obj.end_of_life_date.isoformat() if version_obj.end_of_life_date else None,
            "description": version_obj.description,
            "xsd_file_path": version_obj.xsd_file_path,
        }
    
    async def get_xsd_path(self, version: str) -> Optional[str]:
        """Get path to XSD file for a specific version"""
        version_info = await self.get_version_info(version)
        if version_info and version_info.get("xsd_file_path"):
            return version_info["xsd_file_path"]
        
        # Default XSD path structure
        xsd_path = self.xsd_base_path / f"tiss_{version.replace('.', '_')}.xsd"
        if xsd_path.exists():
            return str(xsd_path)
        
        return None
    
    async def initialize_default_versions(self):
        """Initialize default TISS versions in database"""
        for version in self.SUPPORTED_VERSIONS:
            query = select(TISSVersion).where(TISSVersion.version == version)
            result = await self.db.execute(query)
            existing = result.scalar_one_or_none()
            
            if not existing:
                version_obj = TISSVersion(
                    version=version,
                    is_active=(version == self.CURRENT_TISS_VERSION),
                    xsd_file_path=f"xsd/tiss_{version.replace('.', '_')}.xsd",
                    description=f"TISS Padrão ANS Versão {version}"
                )
                self.db.add(version_obj)
        
        await self.db.commit()
        logger.info("Default TISS versions initialized")

