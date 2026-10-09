from pathlib import PurePosixPath
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import joblog
from ..auth import NODE, issue, lookup, revoke
from ..db import Job, Node, get, now
from ..storage import storage

router = APIRouter(prefix="/v1/nodes")


class Join(BaseModel):
    token: str
    name: str
    env: str = "default"
    gpus: int = 0
    executors: List[str] = ["process"]


class Beat(BaseModel):
    running: List[str] = []


class Claim(BaseModel):
    gpus: int = 0
    executors: List[str] = ["process"]


class Text(BaseModel):
    text: str


class Paths(BaseModel):
    paths: List[str]


class Finish(BaseModel):
    exit_code: int


@router.post("/join")
def join(b: Join, s=Depends(get)):
    t = lookup(s, b.token, {"join"})
    if t.uses is not None:
        t.uses -= 1
    n = Node(name=b.name, env=t.subject or b.env, gpus=b.gpus, executors=b.executors)
    s.add(n)
    s.commit()
    return {"node": n.id, "env": n.env, "token": issue(s, "node", n.id)}


@router.post("/heartbeat")
def heartbeat(b: Beat, s=Depends(get), t=NODE):
    n = s.get(Node, t.subject)
    if n.status == "removed":
        return {"cancel": [], "shutdown": True}
    n.status, n.last_seen = "online", now()
    if b.running:
        n.busy_at = now()
    cancel = [j.id for j in s.query(Job).filter(Job.id.in_(b.running), Job.cancel)] if b.running else []
    s.commit()
    return {"cancel": cancel, "shutdown": False}


@router.post("/claim")
def claim(b: Claim, s=Depends(get), t=NODE):
    n = s.get(Node, t.subject)
    for j in list(s.query(Job).filter_by(status="queued").order_by(Job.created, Job.rank)):
        sp = j.spec
        if sp.get("env") not in (None, n.env) or sp["gpus"] > b.gpus or sp["executor"] not in b.executors:
            continue
        won = s.query(Job).filter_by(id=j.id, status="queued").update({"status": "running", "node": n.id, "started": now()})
        if won != 1:
            continue
        n.busy_at = now()
        s.commit()
        world = s.query(Job).filter_by(group=j.group).count()
        return {"job": {**j.view(), "world": world}, "code_url": storage().presign(f"code/{j.group}.tar.gz"),
                "token": issue(s, "job", j.id, ttl=7 * 86400)}
    return {"job": None}


def _own(s, t, job_id):
    j = s.get(Job, job_id)
    if not j or j.node != t.subject:
        raise HTTPException(403, "not your job")
    return j


@router.post("/jobs/{job_id}/logs")
def logs(job_id: str, b: Text, s=Depends(get), t=NODE):
    _own(s, t, job_id)
    joblog.append(job_id, b.text)
    return {}


@router.post("/jobs/{job_id}/upload")
def upload(job_id: str, b: Paths, s=Depends(get), t=NODE):
    _own(s, t, job_id)
    if any(p.startswith("/") or ".." in PurePosixPath(p).parts for p in b.paths):
        raise HTTPException(400, "bad path")
    return {"urls": {p: storage().presign(f"jobs/{job_id}/outputs/{p}", "PUT") for p in b.paths}}


@router.post("/jobs/{job_id}/finish")
def finish(job_id: str, b: Finish, s=Depends(get), t=NODE):
    j = _own(s, t, job_id)
    j.status = "cancelled" if j.cancel else "succeeded" if b.exit_code == 0 else "failed"
    j.exit_code, j.finished = b.exit_code, now()
    revoke(s, "job", job_id)
    s.commit()
    return j.view()
