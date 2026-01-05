"""
XSD Validator Service
Validates TISS XML against XSD schemas
"""

import logging
from typing import Dict, Optional
from pathlib import Path
import xml.etree.ElementTree as ET
from lxml import etree

from app.services.tiss.versioning import TISSVersioningService

logger = logging.getLogger(__name__)


class XSDValidator:
    """Service for validating TISS XML against XSD schemas"""
    
    def __init__(self, versioning_service: TISSVersioningService):
        self.versioning = versioning_service
    
    async def validate_xml(
        self,
        xml_content: str,
        version: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Validate XML against XSD schema
        
        Args:
            xml_content: XML string to validate
            version: TISS version (defaults to current)
        
        Returns:
            Validation result with errors and warnings
        """
        if version is None:
            version = await self.versioning.get_current_version()
        
        xsd_path = await self.versioning.get_xsd_path(version)
        
        if not xsd_path:
            return {
                "is_valid": False,
                "errors": [f"XSD file not found for version {version}"],
                "warnings": []
            }
        
        errors = []
        warnings = []
        
        try:
            # Parse XML
            xml_doc = etree.fromstring(xml_content.encode('utf-8'))
            
            # Load XSD schema
            xsd_doc = etree.parse(xsd_path)
            xsd_schema = etree.XMLSchema(xsd_doc)
            
            # Validate
            is_valid = xsd_schema.validate(xml_doc)
            
            if not is_valid:
                for error in xsd_schema.error_log:
                    errors.append({
                        "line": error.line,
                        "column": error.column,
                        "message": error.message,
                        "level": "error"
                    })
            
        except etree.XMLSyntaxError as e:
            errors.append({
                "line": e.lineno,
                "message": f"XML syntax error: {str(e)}",
                "level": "error"
            })
        except Exception as e:
            errors.append({
                "message": f"Validation error: {str(e)}",
                "level": "error"
            })
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "version": version
        }

