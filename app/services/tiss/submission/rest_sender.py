"""
REST Sender Service
Sends TISS batches via REST API
"""

import logging
from typing import Dict, Optional
import httpx

from app.models.tiss.batch import TISSBatch

logger = logging.getLogger(__name__)


class RESTSender:
    """Sends TISS batches via REST API"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    async def send_batch(
        self,
        batch: TISSBatch,
        operator_config: Dict
    ) -> Dict[str, any]:
        """
        Send batch via REST
        
        Args:
            batch: TISSBatch object
            operator_config: Operator configuration (URL, credentials, headers)
        
        Returns:
            Result dictionary with status and protocol number
        """
        try:
            url = operator_config.get('rest_url')
            if not url:
                return {
                    "success": False,
                    "error": "REST URL not configured",
                    "protocol_number": None
                }
            
            headers = {
                "Content-Type": "application/xml",
                **operator_config.get('rest_headers', {})
            }
            
            # Add authentication if configured
            auth = operator_config.get('rest_auth')
            if auth:
                if auth.get('type') == 'bearer':
                    headers['Authorization'] = f"Bearer {auth.get('token')}"
                elif auth.get('type') == 'basic':
                    import base64
                    credentials = f"{auth.get('username')}:{auth.get('password')}"
                    encoded = base64.b64encode(credentials.encode()).decode()
                    headers['Authorization'] = f"Basic {encoded}"
            
            xml_content = batch.xml_content or ""
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    content=xml_content,
                    headers=headers
                )
                response.raise_for_status()
                
                # Parse response (format depends on operator)
                protocol_number = None
                if response.headers.get('Content-Type', '').startswith('application/json'):
                    data = response.json()
                    protocol_number = data.get('protocolo') or data.get('protocol_number')
                else:
                    # Try to extract from XML or text response
                    protocol_number = response.text[:100]  # Simplified
            
            return {
                "success": True,
                "protocol_number": protocol_number,
                "message": "Batch sent successfully via REST"
            }
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending batch {batch.id}: {e}")
            return {
                "success": False,
                "error": f"HTTP error: {str(e)}",
                "protocol_number": None
            }
        except Exception as e:
            logger.error(f"Error sending batch {batch.id} via REST: {e}")
            return {
                "success": False,
                "error": str(e),
                "protocol_number": None
            }

