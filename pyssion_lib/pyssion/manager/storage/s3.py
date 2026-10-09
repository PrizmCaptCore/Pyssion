"""Any S3-compatible store: AWS S3, MinIO, GCS (HMAC interop), NHN Object Storage, Cloudflare R2."""
from datetime import timedelta

from minio import Minio


class S3Storage:
    def __init__(self, s):
        self.c = Minio(s.s3_endpoint, s.s3_access, s.s3_secret, secure=s.s3_secure, region=s.s3_region or None)
        self.bucket = s.s3_bucket
        if not self.c.bucket_exists(self.bucket):
            self.c.make_bucket(self.bucket)

    def presign(self, key, method="GET", expires=3600):
        return self.c.get_presigned_url(method, self.bucket, key, expires=timedelta(seconds=expires))

    def list(self, prefix):
        return [o.object_name for o in self.c.list_objects(self.bucket, prefix=prefix, recursive=True)]
