from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import joblog
from ..auth import USER
from ..db import Job, get, new_id, now
from ..storage import storage

router = APIRouter(prefix="/v1/jobs")


class Spec(BaseModel):
    entrypoint: str
    args: List[str] = []
    requirements: Optional[str] = None
    gpus: int = 0
    env: Optional[str] = None
    outputs: str = "outputs"
    executor: str = "process"
    image: Optional[str] = None
    replicas: int = 1


def _job(s, job_id):
    j = s.get(Job, job_id)
    if not j:
        raise HTTPException(404, "no such job")
    return j


@router.post("")
def submit(spec: Spec, s=Depends(get), t=USER):
    group = new_id()
    jobs = [Job(group=group, rank=r, owner=t.subject, spec=spec.model_dump()) for r in range(max(1, spec.replicas))]
    s.add_all(jobs)
    s.commit()
    return {"group": group, "jobs": [j.id for j in jobs], "upload_url": storage().presign(f"code/{group}.tar.gz", "PUT")}


@router.post("/start/{group}")
def start(group: str, s=Depends(get), t=USER):
    n = s.query(Job).filter_by(group=group, status="pending").update({"status": "queued"})
    s.commit()
    return {"queued": n}


@router.get("")
def list_jobs(limit: int = 50, s=Depends(get), t=USER):
    return [j.view() for j in s.query(Job).order_by(Job.created.desc()).limit(limit)]


@router.get("/{job_id}")
def show(job_id: str, s=Depends(get), t=USER):
    return _job(s, job_id).view()


@router.get("/{job_id}/logs")
def logs(job_id: str, offset: int = 0, s=Depends(get), t=USER):
    status = _job(s, job_id).status
    text, offset = joblog.read(job_id, offset)
    return {"text": text, "offset": offset, "status": status}


@router.get("/{job_id}/outputs")
def outputs(job_id: str, s=Depends(get), t=USER):
    _job(s, job_id)
    prefix, st = f"jobs/{job_id}/outputs/", storage()
    return {"files": [{"path": k[len(prefix):], "url": st.presign(k)} for k in st.list(prefix)]}


@router.post("/{job_id}/cancel")
def cancel(job_id: str, s=Depends(get), t=USER):
    j = _job(s, job_id)
    if j.status in ("pending", "queued"):
        j.status, j.finished = "cancelled", now()
    elif j.status == "running":
        j.cancel = True
    s.commit()
    return j.view()
