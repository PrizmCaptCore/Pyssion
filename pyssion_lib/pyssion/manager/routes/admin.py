from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import rods
from ..auth import ADMIN, issue
from ..db import Env, Instance, Node, get

router = APIRouter(prefix="/v1", dependencies=[ADMIN])


class NewToken(BaseModel):
    kind: str = "user"
    subject: str = ""
    uses: Optional[int] = None
    ttl: Optional[float] = None


class EnvIn(BaseModel):
    provisioner: str = "manual"
    config: dict = {}
    max_nodes: int = 1
    ttl: float = 0
    idle: float = 1800


@router.post("/tokens")
def token(b: NewToken, s=Depends(get)):
    if b.kind not in ("admin", "user", "join"):
        raise HTTPException(400, "kind must be admin, user or join")
    return {"token": issue(s, **b.model_dump())}


@router.get("/nodes")
def nodes(s=Depends(get)):
    return [n.view() for n in s.query(Node).order_by(Node.last_seen.desc())]


@router.delete("/nodes/{node_id}")
def remove_node(node_id: str, s=Depends(get)):
    n = s.get(Node, node_id)
    if not n:
        raise HTTPException(404, "no such node")
    n.status = "removed"
    s.commit()
    return {}


@router.get("/envs")
def envs(s=Depends(get)):
    return [{**e.view(), "instances": [i.view() for i in s.query(Instance).filter_by(env=e.name)]} for e in s.query(Env)]


@router.put("/envs/{name}")
def put_env(name: str, b: EnvIn, s=Depends(get)):
    s.merge(Env(name=name, **b.model_dump()))
    s.commit()
    return s.get(Env, name).view()


@router.post("/envs/{name}/up")
def up(name: str, count: int = 1, s=Depends(get)):
    return rods.scale_up(s, name, count)


@router.post("/envs/{name}/down")
def down(name: str, s=Depends(get)):
    return rods.scale_down(s, name)


@router.post("/kill")
def kill(s=Depends(get)):
    return rods.kill(s)
