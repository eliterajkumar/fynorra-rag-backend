"""Supabase Storage helper for file uploads.

Supports two modes:
- Default: Supabase client SDK
- Optional: S3-compatible mode using boto3 against Supabase Storage S3 endpoint
"""
from supabase import create_client, Client
from src.config import Config
from typing import Optional
import uuid
import io

try:
    import boto3  # optional
except Exception:  # pragma: no cover
    boto3 = None


class SupabaseStorage:
    """Helper for Supabase Storage operations."""
    
    def __init__(self):
        """Initialize storage clients based on configuration."""
        self.bucket_name = Config.SUPABASE_BUCKET
        self.use_s3 = Config.SUPABASE_S3_ENABLED
        if self.use_s3:
            if boto3 is None:
                raise RuntimeError("boto3 is required for S3 mode; please install it")
            if not (Config.SUPABASE_S3_ENDPOINT and Config.SUPABASE_S3_ACCESS_KEY_ID and Config.SUPABASE_S3_SECRET_ACCESS_KEY):
                raise ValueError("S3 mode requires SUPABASE_S3_ENDPOINT, SUPABASE_S3_ACCESS_KEY_ID, SUPABASE_S3_SECRET_ACCESS_KEY")
            self.s3 = boto3.client(
                "s3",
                endpoint_url=Config.SUPABASE_S3_ENDPOINT,
                aws_access_key_id=Config.SUPABASE_S3_ACCESS_KEY_ID,
                aws_secret_access_key=Config.SUPABASE_S3_SECRET_ACCESS_KEY,
                region_name=Config.SUPABASE_S3_REGION or None,
            )
        else:
            self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
            self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Ensure storage bucket exists."""
        if self.use_s3:
            # Best-effort create via S3 API
            try:
                self.s3.create_bucket(Bucket=self.bucket_name)
            except Exception:
                pass
        else:
            try:
                buckets = self.client.storage.list_buckets()
                bucket_names = [b.name for b in buckets]
                if self.bucket_name not in bucket_names:
                    self.client.storage.create_bucket(self.bucket_name, public=False)
            except Exception:
                # Bucket might already exist or other error
                pass
    
    def upload_file(self, file_content: bytes, file_name: str, user_id: str, folder: str = "uploads") -> str:
        """
        Upload file to Supabase Storage.
        
        Args:
            file_content: File content as bytes
            file_name: Original file name
            user_id: User ID for organization
            folder: Folder path in bucket
        
        Returns:
            Storage path
        """
        # Generate unique path
        file_extension = file_name.split(".")[-1] if "." in file_name else ""
        unique_name = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
        storage_path = f"{folder}/{user_id}/{unique_name}"
        
        # Upload file
        if self.use_s3:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=storage_path,
                Body=io.BytesIO(file_content),
                ContentType="application/octet-stream",
            )
        else:
            self.client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": "application/octet-stream"}
            )
        
        return storage_path
    
    def download_file(self, storage_path: str) -> bytes:
        """Download file from Supabase Storage."""
        if self.use_s3:
            obj = self.s3.get_object(Bucket=self.bucket_name, Key=storage_path)
            return obj["Body"].read()
        else:
            response = self.client.storage.from_(self.bucket_name).download(storage_path)
            return response
    
    def delete_file(self, storage_path: str):
        """Delete file from Supabase Storage."""
        if self.use_s3:
            self.s3.delete_object(Bucket=self.bucket_name, Key=storage_path)
        else:
            self.client.storage.from_(self.bucket_name).remove([storage_path])
    
    def get_public_url(self, storage_path: str) -> Optional[str]:
        """Get public URL for file (if bucket is public)."""
        if self.use_s3:
            # Not directly supported; would require signed URLs with S3
            try:
                params = {"Bucket": self.bucket_name, "Key": storage_path}
                url = self.s3.generate_presigned_url("getObject", Params=params, ExpiresIn=3600)
                return url
            except Exception:
                return None
        else:
            try:
                response = self.client.storage.from_(self.bucket_name).get_public_url(storage_path)
                return response
            except Exception:
                return None

