"""
SOAP Sender Service
Sends TISS batches via SOAP protocol
"""

import logging
from typing import Dict, Optional
from zeep import Client
from zeep.exceptions import Fault

from app.models.tiss.batch import TISSBatch

logger = logging.getLogger(__name__)


class SOAPSender:
    """Sends TISS batches via SOAP"""
    
    def __init__(self, wsdl_url: str, timeout: int = 30):
        self.wsdl_url = wsdl_url
        self.timeout = timeout
        self.client = None
    
    async def send_batch(
        self,
        batch: TISSBatch,
        operator_config: Dict
    ) -> Dict[str, any]:
        """
        Send batch via SOAP
        
        Args:
            batch: TISSBatch object
            operator_config: Operator configuration (credentials, endpoints)
        
        Returns:
            Result dictionary with status and protocol number
        """
        try:
            if not self.client:
                self.client = Client(self.wsdl_url, timeout=self.timeout)
            
            # Prepare SOAP request
            xml_content = batch.xml_content or ""
            
            # Call SOAP service (method name depends on operator)
            method_name = operator_config.get('soap_method', 'enviarLoteGuias')
            response = self.client.service[method_name](
                xml_content=xml_content,
                numero_lote=batch.numero_lote,
                **operator_config.get('soap_params', {})
            )
            
            # Parse response
            protocol_number = response.get('protocolo') if isinstance(response, dict) else str(response)
            
            return {
                "success": True,
                "protocol_number": protocol_number,
                "message": "Batch sent successfully via SOAP"
            }
            
        except Fault as e:
            logger.error(f"SOAP fault sending batch {batch.id}: {e}")
            return {
                "success": False,
                "error": f"SOAP fault: {str(e)}",
                "protocol_number": None
            }
        except Exception as e:
            logger.error(f"Error sending batch {batch.id} via SOAP: {e}")
            return {
                "success": False,
                "error": str(e),
                "protocol_number": None
            }

