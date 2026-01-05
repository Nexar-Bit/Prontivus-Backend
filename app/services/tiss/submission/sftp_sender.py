"""
SFTP Sender Service
Sends TISS batches via SFTP protocol
"""

import logging
from typing import Dict, Optional
from pathlib import Path
import paramiko
from io import StringIO

from app.models.tiss.batch import TISSBatch

logger = logging.getLogger(__name__)


class SFTPSender:
    """Sends TISS batches via SFTP"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    async def send_batch(
        self,
        batch: TISSBatch,
        operator_config: Dict
    ) -> Dict[str, any]:
        """
        Send batch via SFTP
        
        Args:
            batch: TISSBatch object
            operator_config: Operator configuration (host, port, credentials, paths)
        
        Returns:
            Result dictionary with status
        """
        try:
            host = operator_config.get('sftp_host')
            port = operator_config.get('sftp_port', 22)
            username = operator_config.get('sftp_username')
            password = operator_config.get('sftp_password')
            private_key = operator_config.get('sftp_private_key')
            remote_path = operator_config.get('sftp_remote_path', '/incoming')
            
            if not host or not username:
                return {
                    "success": False,
                    "error": "SFTP host and username required",
                    "protocol_number": None
                }
            
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect
            if private_key:
                # Use key-based authentication
                key = paramiko.RSAKey.from_private_key(StringIO(private_key))
                ssh.connect(host, port=port, username=username, pkey=key, timeout=self.timeout)
            else:
                # Use password authentication
                ssh.connect(host, port=port, username=username, password=password, timeout=self.timeout)
            
            # Create SFTP client
            sftp = ssh.open_sftp()
            
            # Upload file
            filename = f"lote_{batch.numero_lote}.xml"
            remote_file_path = f"{remote_path}/{filename}"
            
            xml_content = batch.xml_content or ""
            file_obj = StringIO(xml_content)
            
            sftp.putfo(file_obj, remote_file_path)
            
            # Close connections
            sftp.close()
            ssh.close()
            
            return {
                "success": True,
                "protocol_number": filename,  # SFTP doesn't return protocol, use filename
                "message": f"Batch uploaded successfully to {remote_file_path}"
            }
            
        except paramiko.AuthenticationException as e:
            logger.error(f"SFTP authentication error for batch {batch.id}: {e}")
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}",
                "protocol_number": None
            }
        except Exception as e:
            logger.error(f"Error sending batch {batch.id} via SFTP: {e}")
            return {
                "success": False,
                "error": str(e),
                "protocol_number": None
            }

