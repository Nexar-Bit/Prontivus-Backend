"""
TISS Statement Parser
Parses return statements from operators
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class StatementParser:
    """Parser for TISS return statements"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def parse_statement_xml(self, xml_content: str) -> Dict:
        """
        Parse statement XML and extract statement information
        
        Args:
            xml_content: XML string from operator
            
        Returns:
            Dictionary with parsed statement data
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Extract statement information
            statement_number = self._extract_text(root, './/numeroDemonstrativo') or \
                             self._extract_text(root, './/numeroDemonstrativoRetorno')
            
            statement_date = self._extract_text(root, './/dataDemonstrativo') or \
                           self._extract_text(root, './/dataEmissao')
            
            # Extract operator information
            operator_cnpj = self._extract_text(root, './/cnpjOperadora')
            operator_name = self._extract_text(root, './/nomeOperadora')
            
            # Extract provider information
            provider_cnpj = self._extract_text(root, './/cnpjPrestador')
            provider_name = self._extract_text(root, './/nomePrestador')
            
            # Extract financial information
            total_value = self._extract_text(root, './/valorTotal') or \
                        self._extract_text(root, './/valorTotalDemonstrativo')
            
            approved_value = self._extract_text(root, './/valorAprovado') or \
                           self._extract_text(root, './/valorTotalAprovado')
            
            rejected_value = self._extract_text(root, './/valorRejeitado') or \
                           self._extract_text(root, './/valorTotalRejeitado')
            
            # Extract guides information
            guides = []
            for guide_elem in root.findall('.//guia'):
                guide_data = {
                    'guide_number': self._extract_text(guide_elem, './/numeroGuia'),
                    'guide_type': self._extract_text(guide_elem, './/tipoGuia'),
                    'status': self._extract_text(guide_elem, './/situacao'),
                    'value': self._extract_text(guide_elem, './/valor'),
                    'rejections': []
                }
                
                # Extract rejections for this guide
                for rejection_elem in guide_elem.findall('.//motivoGlosa'):
                    guide_data['rejections'].append({
                        'code': self._extract_text(rejection_elem, './/codigoGlosa'),
                        'description': self._extract_text(rejection_elem, './/descricaoGlosa'),
                        'value': self._extract_text(rejection_elem, './/valorGlosa')
                    })
                
                guides.append(guide_data)
            
            statement_data = {
                'statement_number': statement_number,
                'statement_date': statement_date,
                'operator_cnpj': operator_cnpj,
                'operator_name': operator_name,
                'provider_cnpj': provider_cnpj,
                'provider_name': provider_name,
                'total_value': total_value,
                'approved_value': approved_value,
                'rejected_value': rejected_value,
                'guides': guides,
                'parsed_at': datetime.now().isoformat(),
                'raw_xml': xml_content
            }
            
            logger.info(f"Parsed statement {statement_number} with {len(guides)} guides")
            return statement_data
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            raise ValueError(f"Invalid XML format: {e}")
        except Exception as e:
            logger.error(f"Error parsing statement XML: {e}")
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
    
    async def validate_statement(self, statement_data: Dict) -> Dict[str, any]:
        """Validate parsed statement data"""
        errors = []
        
        if not statement_data.get('statement_number'):
            errors.append("Statement number is required")
        
        if not statement_data.get('statement_date'):
            errors.append("Statement date is required")
        
        if not statement_data.get('operator_cnpj'):
            errors.append("Operator CNPJ is required")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }

