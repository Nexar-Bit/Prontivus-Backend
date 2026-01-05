"""
TISS Protocol Parser
Parses protocol receipts from operators
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class ProtocolParser:
    """Parser for TISS protocol receipts"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def parse_protocol_xml(self, xml_content: str) -> Dict:
        """
        Parse protocol XML and extract protocol information
        
        Args:
            xml_content: XML string from operator
            
        Returns:
            Dictionary with parsed protocol data
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Extract protocol number
            protocol_number = self._extract_text(root, './/numeroProtocolo') or \
                            self._extract_text(root, './/numeroProtocoloRecebimento')
            
            # Extract date/time
            protocol_date = self._extract_text(root, './/dataProtocolo') or \
                          self._extract_text(root, './/dataRecebimento')
            
            protocol_time = self._extract_text(root, './/horaProtocolo') or \
                          self._extract_text(root, './/horaRecebimento')
            
            # Extract batch information
            batch_number = self._extract_text(root, './/numeroLote') or \
                         self._extract_text(root, './/numeroLoteGuia')
            
            # Extract operator information
            operator_cnpj = self._extract_text(root, './/cnpjOperadora')
            operator_name = self._extract_text(root, './/nomeOperadora')
            
            # Extract status
            status = self._extract_text(root, './/situacao') or \
                    self._extract_text(root, './/status')
            
            # Extract validation errors if any
            errors = []
            for error_elem in root.findall('.//erro'):
                errors.append({
                    'code': self._extract_text(error_elem, './/codigo'),
                    'message': self._extract_text(error_elem, './/mensagem'),
                    'severity': self._extract_text(error_elem, './/severidade', default='ERROR')
                })
            
            protocol_data = {
                'protocol_number': protocol_number,
                'protocol_date': protocol_date,
                'protocol_time': protocol_time,
                'batch_number': batch_number,
                'operator_cnpj': operator_cnpj,
                'operator_name': operator_name,
                'status': status,
                'errors': errors,
                'parsed_at': datetime.now().isoformat(),
                'raw_xml': xml_content
            }
            
            logger.info(f"Parsed protocol {protocol_number} for batch {batch_number}")
            return protocol_data
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            raise ValueError(f"Invalid XML format: {e}")
        except Exception as e:
            logger.error(f"Error parsing protocol XML: {e}")
            raise
    
    def _extract_text(self, root: ET.Element, xpath: str, default: Optional[str] = None) -> Optional[str]:
        """Extract text content from XML element"""
        try:
            elem = root.find(xpath)
            if elem is not None and elem.text:
                return elem.text.strip()
        except Exception:
            pass
        return default
    
    async def validate_protocol(self, protocol_data: Dict) -> Dict[str, any]:
        """Validate parsed protocol data"""
        errors = []
        
        if not protocol_data.get('protocol_number'):
            errors.append("Protocol number is required")
        
        if not protocol_data.get('protocol_date'):
            errors.append("Protocol date is required")
        
        if not protocol_data.get('batch_number'):
            errors.append("Batch number is required")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }

