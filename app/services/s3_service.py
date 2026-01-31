"""
AWS S3 Service
Handles PDF report storage, retrieval, and management in S3
"""

import os
import logging
from typing import Optional, BinaryIO
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
from io import BytesIO

logger = logging.getLogger(__name__)


class S3Service:
    """Service for managing PDF reports in AWS S3"""
    
    def __init__(self):
        """Initialize S3 client"""
        self.enabled = False
        self.s3_client = None
        self.bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        # Get AWS credentials
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        if not all([aws_access_key, aws_secret_key, self.bucket_name]):
            logger.warning("AWS S3 not configured. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_S3_BUCKET_NAME")
            return
        
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=self.region
            )
            
            # Verify bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            self.enabled = True
            logger.info(f"AWS S3 initialized. Bucket: {self.bucket_name}, Region: {self.region}")
        except Exception as e:
            logger.error(f"Failed to initialize AWS S3: {str(e)}")
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if S3 is enabled"""
        return self.enabled
    
    def generate_report_key(
        self,
        clinic_id: int,
        report_type: str,
        report_id: Optional[int] = None,
        extension: str = "pdf"
    ) -> str:
        """
        Generate S3 key for report storage
        
        Format: clinics/{clinic_id}/reports/{report_type}/{year}/{month}/{report_id}_{timestamp}.{extension}
        """
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        
        if report_id:
            filename = f"{report_id}_{timestamp}.{extension}"
        else:
            filename = f"{timestamp}.{extension}"
        
        key = f"clinics/{clinic_id}/reports/{report_type}/{year}/{month}/{filename}"
        return key
    
    async def upload_report(
        self,
        file_content: bytes,
        clinic_id: int,
        report_type: str,
        report_id: Optional[int] = None,
        filename: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Upload PDF report to S3
        
        Args:
            file_content: PDF file content as bytes
            clinic_id: Clinic ID
            report_type: Type of report (billing, sales, stock, etc.)
            report_id: Optional report ID
            filename: Optional custom filename
            metadata: Optional metadata dict
            
        Returns:
            {
                "success": bool,
                "key": str,
                "url": str,
                "bucket": str,
                "size": int
            }
        """
        if not self.enabled:
            raise Exception("AWS S3 is not enabled. Configure AWS credentials.")
        
        try:
            # Generate S3 key
            if filename:
                key = f"clinics/{clinic_id}/reports/{report_type}/{filename}"
            else:
                key = self.generate_report_key(clinic_id, report_type, report_id)
            
            # Prepare metadata
            upload_metadata = {
                "clinic_id": str(clinic_id),
                "report_type": report_type,
                "uploaded_at": datetime.now().isoformat()
            }
            
            if report_id:
                upload_metadata["report_id"] = str(report_id)
            
            if metadata:
                upload_metadata.update(metadata)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType='application/pdf',
                Metadata=upload_metadata,
                ServerSideEncryption='AES256'  # Enable encryption at rest
            )
            
            # Generate URL
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
            
            logger.info(f"Uploaded report to S3: {key}")
            
            return {
                "success": True,
                "key": key,
                "url": url,
                "bucket": self.bucket_name,
                "size": len(file_content),
                "region": self.region
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"S3 upload error ({error_code}): {error_message}")
            raise Exception(f"Failed to upload report: {error_message}")
        except Exception as e:
            logger.error(f"Error uploading report to S3: {str(e)}", exc_info=True)
            raise
    
    async def download_report(
        self,
        key: str
    ) -> bytes:
        """
        Download PDF report from S3
        
        Args:
            key: S3 object key
            
        Returns:
            PDF file content as bytes
        """
        if not self.enabled:
            raise Exception("AWS S3 is not enabled")
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            file_content = response['Body'].read()
            
            logger.info(f"Downloaded report from S3: {key}")
            
            return file_content
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                raise Exception("Report not found in S3")
            else:
                error_message = e.response.get('Error', {}).get('Message', str(e))
                logger.error(f"S3 download error ({error_code}): {error_message}")
                raise Exception(f"Failed to download report: {error_message}")
        except Exception as e:
            logger.error(f"Error downloading report from S3: {str(e)}", exc_info=True)
            raise
    
    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        download: bool = True
    ) -> str:
        """
        Generate presigned URL for temporary access to report
        
        Args:
            key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            download: If True, force download; if False, allow inline view
            
        Returns:
            Presigned URL
        """
        if not self.enabled:
            raise Exception("AWS S3 is not enabled")
        
        try:
            params = {
                'Bucket': self.bucket_name,
                'Key': key
            }
            
            if download:
                params['ResponseContentDisposition'] = f'attachment; filename="{key.split("/")[-1]}"'
            else:
                params['ResponseContentDisposition'] = 'inline'
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for: {key}")
            
            return url
            
        except ClientError as e:
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Error generating presigned URL: {error_message}")
            raise Exception(f"Failed to generate download URL: {error_message}")
        except Exception as e:
            logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
            raise
    
    async def delete_report(
        self,
        key: str
    ) -> bool:
        """
        Delete report from S3
        
        Args:
            key: S3 object key
            
        Returns:
            True if successful
        """
        if not self.enabled:
            raise Exception("AWS S3 is not enabled")
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"Deleted report from S3: {key}")
            
            return True
            
        except ClientError as e:
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Error deleting report: {error_message}")
            raise Exception(f"Failed to delete report: {error_message}")
        except Exception as e:
            logger.error(f"Error deleting report from S3: {str(e)}", exc_info=True)
            raise
    
    async def list_reports(
        self,
        clinic_id: int,
        report_type: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> list:
        """
        List reports for a clinic
        
        Args:
            clinic_id: Clinic ID
            report_type: Optional filter by report type
            prefix: Optional custom prefix
            
        Returns:
            List of report objects
        """
        if not self.enabled:
            raise Exception("AWS S3 is not enabled")
        
        try:
            # Build prefix
            if prefix:
                list_prefix = prefix
            elif report_type:
                list_prefix = f"clinics/{clinic_id}/reports/{report_type}/"
            else:
                list_prefix = f"clinics/{clinic_id}/reports/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=list_prefix
            )
            
            reports = []
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    reports.append({
                        "key": obj['Key'],
                        "size": obj['Size'],
                        "last_modified": obj['LastModified'].isoformat(),
                        "etag": obj['ETag']
                    })
            
            logger.info(f"Listed {len(reports)} reports for clinic {clinic_id}")
            
            return reports
            
        except ClientError as e:
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Error listing reports: {error_message}")
            raise Exception(f"Failed to list reports: {error_message}")
        except Exception as e:
            logger.error(f"Error listing reports from S3: {str(e)}", exc_info=True)
            raise
    
    async def get_report_metadata(
        self,
        key: str
    ) -> dict:
        """
        Get report metadata from S3
        
        Args:
            key: S3 object key
            
        Returns:
            Metadata dict
        """
        if not self.enabled:
            raise Exception("AWS S3 is not enabled")
        
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return {
                "key": key,
                "size": response['ContentLength'],
                "last_modified": response['LastModified'].isoformat(),
                "content_type": response.get('ContentType'),
                "metadata": response.get('Metadata', {}),
                "etag": response.get('ETag')
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NotFound' or error_code == '404':
                raise Exception("Report not found in S3")
            else:
                error_message = e.response.get('Error', {}).get('Message', str(e))
                logger.error(f"Error getting metadata: {error_message}")
                raise Exception(f"Failed to get report metadata: {error_message}")
        except Exception as e:
            logger.error(f"Error getting report metadata from S3: {str(e)}", exc_info=True)
            raise


# Global S3 service instance
s3_service = S3Service()
