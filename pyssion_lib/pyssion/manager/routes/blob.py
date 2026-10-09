"""Serves presigned URLs when storage is `local` (the manager's own disk)."""
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ..storage import storage
from ..storage.local import LocalStorage

router = APIRouter()


@router.api_route("/blob/{key:path}", methods=["GET", "PUT"])
async def blob(key: str, request: Request, m: str, e: int, s: str):
    st = storage()
    if not isinstance(st, LocalStorage) or m != request.method or not st.verify(key, m, e, s):
        raise HTTPException(403, "bad signature")
    p = st.path(key)
    if m == "GET":
        if not p.is_file():
            raise HTTPException(404, "no such blob")
        return FileResponse(p, media_type="application/octet-stream")
    tmp = st.root.parent / "tmp" / uuid.uuid4().hex
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "wb") as f:
        async for chunk in request.stream():
            f.write(chunk)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp.replace(p)
    return {}
