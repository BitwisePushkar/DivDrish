"""
AWS S3 Service utility.

Handles file uploads to S3 and returns public URLs.
"""
import os
import boto3
from botocore.exceptions import ClientError
from app.config.settings import get_config
from app.utils.logger import logger

class S3Service:
    def __init__(self):
        config = get_config()
        self.bucket = config.AWS_S3_BUCKET
        self.region = config.AWS_REGION
        self.custom_domain = config.AWS_S3_CUSTOM_DOMAIN
        
        # Initialize client only if keys are provided
        if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
            self.client = boto3.client(
                "s3",
                aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                region_name=self.region
            )
        else:
            self.client = None
            logger.warning("AWS S3 credentials not configured. S3 uploads will fail.")

    def upload_file(self, local_path: str, object_name: str, content_type: str = None) -> str | None:
        """
        Uploads a file to S3 and returns the public URL.
        """
        if not self.client:
            logger.error("S3 client not initialized. Cannot upload.")
            return None

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
            
        # We assume the bucket is configured for public read if this is for community sharing.
        # Otherwise, you would use presigned URLs.
        # But for community sharing, public URLs are standard.
        try:
            self.client.upload_file(
                local_path, 
                self.bucket, 
                object_name,
                ExtraArgs=extra_args
            )
            
            if self.custom_domain:
                url = f"https://{self.custom_domain}/{object_name}"
            else:
                url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{object_name}"
                
            logger.info(f"File uploaded to S3: {url}")
            return url
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            return None

# Singleton instance
s3_service = S3Service()
