import logging
import os

import boto3
from botocore.client import Config

from src.config.settings import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        storage_cfg = settings.storage
        endpoint = storage_cfg.minio_url
        if not endpoint.startswith("http"):
            endpoint = f"http://{endpoint}"

        logger.info(
            "Connecting to MinIO at %s (bucket=%s)", endpoint, storage_cfg.minio_bucket
        )
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=storage_cfg.minio_root_user,
            aws_secret_access_key=storage_cfg.minio_root_password,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = storage_cfg.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.s3.head_bucket(Bucket=self.bucket)
            logger.info("Bucket '%s' exists", self.bucket)
        except Exception as e:
            logger.warning("Bucket '%s' not found (%s), creating...", self.bucket, e)
            self.s3.create_bucket(Bucket=self.bucket)
            logger.info("Bucket '%s' created", self.bucket)

    def upload_file(self, local_path: str, s3_key: str | None = None) -> str:
        if s3_key is None:
            s3_key = local_path
        self.s3.upload_file(local_path, self.bucket, s3_key)
        return s3_key

    def upload_directory(self, local_dir: str, s3_prefix: str) -> list[str]:
        uploaded_keys = []
        for root, _dirs, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, local_dir)
                s3_key = os.path.join(s3_prefix, relative_path).replace("\\", "/")
                key = self.upload_file(local_path, s3_key)
                uploaded_keys.append(key)
        return uploaded_keys

    def copy_file(self, source_key: str, dest_key: str):
        copy_source = {"Bucket": self.bucket, "Key": source_key}
        self.s3.copy(copy_source, self.bucket, dest_key)

    def download_file(self, s3_key: str, local_path: str) -> str:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        self.s3.download_file(self.bucket, s3_key, local_path)
        return local_path

    def download_directory(self, s3_prefix: str, local_dir: str):
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=s3_prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    s3_key = obj["Key"]
                    relative_path = os.path.relpath(s3_key, s3_prefix)
                    local_path = os.path.join(local_dir, relative_path)
                    self.download_file(s3_key, local_path)

    def delete_file(self, s3_key: str):
        self.s3.delete_object(Bucket=self.bucket, Key=s3_key)

    def list_files(self, prefix: str = "", extension: str | None = None) -> list[dict]:
        paginator = self.s3.get_paginator("list_objects_v2")
        files = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    key = obj["Key"]
                    if extension and not key.lower().endswith(extension.lower()):
                        continue
                    files.append(
                        {
                            "key": key,
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"].isoformat(),
                            "path": key,
                        }
                    )
        return files

    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": s3_key},
            ExpiresIn=expires_in,
        )
