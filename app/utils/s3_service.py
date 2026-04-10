"""
AWS S3 Service utility.

Handles file uploads to S3 and returns public URLs.
Uses lazy initialization to avoid import-time issues.
"""
import os
import mimetypes
import boto3
from botocore.exceptions import ClientError
from app.utils.logger import logger


class S3Service:
    """Lazy-initialized S3 client that defers boto3 setup until first use."""

    def __init__(self):
        self._client = None
        self._initialized = False
        self.bucket = None
        self.region = None
        self.custom_domain = None

    def _ensure_initialized(self):
        """Initialize S3 client on first use, reading config at call time."""
        if self._initialized:
            return

        from app.config.settings import get_config
        config = get_config()

        self.bucket = config.AWS_S3_BUCKET
        self.region = config.AWS_REGION or "us-east-1"
        self.custom_domain = config.AWS_S3_CUSTOM_DOMAIN

        if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY and self.bucket:
            try:
                self._client = boto3.client(
                    "s3",
                    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                    region_name=self.region,
                )
                logger.info(f"S3 client initialized for bucket '{self.bucket}' in '{self.region}'")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                self._client = None
        else:
            self._client = None
            missing = []
            if not config.AWS_ACCESS_KEY_ID:
                missing.append("AWS_ACCESS_KEY_ID")
            if not config.AWS_SECRET_ACCESS_KEY:
                missing.append("AWS_SECRET_ACCESS_KEY")
            if not self.bucket:
                missing.append("AWS_S3_BUCKET")
            logger.warning(f"AWS S3 not configured (missing: {', '.join(missing)}). S3 uploads will be skipped.")

        self._initialized = True

    @property
    def is_available(self) -> bool:
        """Check if S3 service is properly configured and available."""
        self._ensure_initialized()
        return self._client is not None

    def upload_file(self, local_path: str, object_name: str, content_type: str = None) -> str | None:
        """
        Uploads a file to S3 and returns the public URL.

        Args:
            local_path: Path to the local file.
            object_name: The S3 object key (path in bucket).
            content_type: Optional MIME type override.

        Returns:
            The public URL on success, or None on failure.
        """
        self._ensure_initialized()

        if not self._client:
            logger.warning("S3 client not available. Skipping upload.")
            return None

        if not os.path.exists(local_path):
            logger.error(f"File not found for S3 upload: {local_path}")
            return None

        # Auto-detect content type from filename if not provided
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        else:
            guessed_type, _ = mimetypes.guess_type(local_path)
            if guessed_type:
                extra_args["ContentType"] = guessed_type

        try:
            self._client.upload_file(
                local_path,
                self.bucket,
                object_name,
                ExtraArgs=extra_args,
            )

            if self.custom_domain:
                url = f"https://{self.custom_domain}/{object_name}"
            else:
                url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{object_name}"

            logger.info(f"File uploaded to S3: {url}")
            return url

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"S3 upload failed (AWS error {error_code}): {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            return None

    def delete_file(self, object_name: str) -> bool:
        """Delete a file from S3."""
        self._ensure_initialized()

        if not self._client:
            logger.warning("S3 client not available. Cannot delete.")
            return False

        try:
            self._client.delete_object(Bucket=self.bucket, Key=object_name)
            logger.info(f"S3 object deleted: {object_name}")
            return True
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}")
            return False


# Singleton instance (lazy — no boto3 call at import time)
s3_service = S3Service()
