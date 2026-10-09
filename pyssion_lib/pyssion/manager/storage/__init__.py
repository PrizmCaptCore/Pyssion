"""Where code, outputs and reactor weights live. Everything moves by presigned URL, never through the API."""
from functools import cache

from ..settings import settings


@cache
def storage():
    if settings.storage == "s3":
        from .s3 import S3Storage
        return S3Storage(settings)
    from .local import LocalStorage
    return LocalStorage(settings)


__all__ = ["storage"]
