"""
TISS Payment Parser
Parses payment statements from operators
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class PaymentParser:
    """Parser for TISS payment statements"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def parse_payment_xml(self, xml_content: str) -> Dict:
        """
        Parse payment XML and extract payment information
        
        Args:
            xml_content: XML string from operator
            
        Returns:
            Dictionary with parsed payment data
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Extract payment information
            payment_number = self._extract_text(root, './/numeroPagamento') or \
                           self._extract_text(root, './/numeroDemonstrativoPagamento')
            
            payment_date = self._extract_text(root, './/dataPagamento') or \
                         self._extract_text(root, './/dataLiquidacao')
            
            due_date = self._extract_text(root, './/dataVencimento')
            
            # Extract operator information
            operator_cnpj = self._extract_text(root, './/cnpjOperadora')
            operator_name = self._extract_text(root, './/nomeOperadora')
            
            # Extract provider information
            provider_cnpj = self._extract_text(root, './/cnpjPrestador')
            provider_name = self._extract_text(root, './/nomePrestador')
            
            # Extract financial information
            total_value = self._extract_text(root, './/valorTotal') or \
                        self._extract_text(root, './/valorTotalPago')
            
            net_value = self._extract_text(root, './/valorLiquido') or \
                       self._extract_text(root, './/valorLiquidoPagamento')
            
            discounts = self._extract_text(root, './/valorDescontos') or \
                       self._extract_text(root, './/totalDescontos')
            
            # Extract payment method
            payment_method = self._extract_text(root, './/formaPagamento') or \
                           self._extract_text(root, './/metodoPagamento')
            
            # Extract bank information
            bank_code = self._extract_text(root, './/codigoBanco')
            bank_name = self._extract_text(root, './/nomeBanco')
            agency = self._extract_text(root, './/agencia')
            account = self._extract_text(root, './/conta')
            
            # Extract statements linked to this payment
            statements = []
            for stmt_elem in root.findall('.//demonstrativo'):
                statements.append({
                    'statement_number': self._extract_text(stmt_elem, './/numeroDemonstrativo'),
                    'statement_date': self._extract_text(stmt_elem, './/dataDemonstrativo'),
                    'value': self._extract_text(stmt_elem, './/valor')
                })
            
            payment_data = {
                'payment_number': payment_number,
                'payment_date': payment_date,
                'due_date': due_date,
                'operator_cnpj': operator_cnpj,
                'operator_name': operator_name,
                'provider_cnpj': provider_cnpj,
                'provider_name': provider_name,
                'total_value': total_value,
                'net_value': net_value,
                'discounts': discounts,
                'payment_method': payment_method,
                'bank_code': bank_code,
                'bank_name': bank_name,
                'agency': agency,
                'account': account,
                'statements': statements,
                'parsed_at': datetime.now().isoformat(),
                'raw_xml': xml_content
            }
            
            logger.info(f"Parsed payment {payment_number}")
            return payment_data
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            raise ValueError(f"Invalid XML format: {e}")
        except Exception as e:
            logger.error(f"Error parsing payment XML: {e}")
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
    
    async def validate_payment(self, payment_data: Dict) -> Dict[str, any]:
        """Validate parsed payment data"""
        errors = []
        
        if not payment_data.get('payment_number'):
            errors.append("Payment number is required")
        
        if not payment_data.get('payment_date'):
            errors.append("Payment date is required")
        
        if not payment_data.get('operator_cnpj'):
            errors.append("Operator CNPJ is required")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }

