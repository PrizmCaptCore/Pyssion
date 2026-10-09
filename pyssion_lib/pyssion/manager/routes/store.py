"""Presigned access to reactor/<session>/... for training jobs (job tokens) and users."""
from pathlib import PurePosixPath

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..auth import STORE
from ..storage import storage

router = APIRouter(prefix="/v1/store")


class Url(BaseModel):
    key: str
    method: str = "GET"


def _check(key):
    if not key.startswith("reactor/") or ".." in PurePosixPath(key).parts:
        raise HTTPException(403, "reactor/ keys only")


@router.post("/url")
def url(b: Url, t=STORE):
    _check(b.key)
    if b.method not in ("GET", "PUT"):
        raise HTTPException(400, "GET or PUT")
    return {"url": storage().presign(b.key, b.method)}


@router.get("/list")
def list_keys(prefix: str, t=STORE):
    _check(prefix)
    return {"keys": storage().list(prefix)}
