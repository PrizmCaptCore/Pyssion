"""Control rods: everything that keeps the chain reaction bounded.

- max_nodes per env when scaling up
- ttl and idle limits that destroy provisioned machines
- nodes that stop heartbeating go offline and their jobs are marked lost
- machines that never join are destroyed
- kill switch: cancel every job and destroy every provisioned machine
"""
import threading
import traceback

from fastapi import HTTPException

from . import joblog
from .auth import issue
from .db import Env, Instance, Job, Node, Session, new_id, now
from .provision import provisioner
from .settings import settings

NEVER_JOINED = 1800


def scale_up(s, env_name, count):
    env = s.get(Env, env_name)
    if not env:
        raise HTTPException(404, "no such env")
    live = s.query(Instance).filter_by(env=env_name).count()
    if live + count > env.max_nodes:
        raise HTTPException(409, f"control rod: {env_name} allows {env.max_nodes} node(s), {live} alive")
    try:
        p = provisioner(env)
    except ValueError as e:
        raise HTTPException(400, str(e))
    names = []
    for _ in range(count):
        name = f"{env_name}-{new_id()[:6]}"
        token = issue(s, "join", env_name, uses=1, ttl=3600)
        s.add(Instance(name=name, env=env_name, expires=now() + env.ttl if env.ttl else None))
        s.commit()
        threading.Thread(target=_up, args=(p, name, token), daemon=True).start()
        names.append(name)
    return {"instances": names}


def _up(p, name, token):
    try:
        ref = p.up(name, settings.public_url, token)
        with Session() as s:
            s.query(Instance).filter_by(name=name).update({"ref": ref, "status": "up"})
            s.commit()
    except Exception:
        joblog.append(f"provision-{name}", traceback.format_exc())
        with Session() as s:
            s.query(Instance).filter_by(name=name).delete()
            s.commit()


def destroy(s, inst):
    try:
        provisioner(s.get(Env, inst.env)).down(inst.ref or inst.name)
    except Exception:
        joblog.append(f"provision-{inst.name}", traceback.format_exc())
        return False
    s.query(Node).filter_by(name=inst.name).update({"status": "removed"})
    s.delete(inst)
    s.commit()
    return True


def scale_down(s, env_name):
    return {"destroyed": [i.name for i in list(s.query(Instance).filter_by(env=env_name)) if destroy(s, i)]}


def kill(s):
    cancelled = s.query(Job).filter(Job.status.in_(["pending", "queued"])).update({"status": "cancelled", "finished": now()})
    stopping = s.query(Job).filter_by(status="running").update({"cancel": True})
    s.commit()
    destroyed = [i.name for i in list(s.query(Instance)) if destroy(s, i)]
    return {"cancelled": cancelled, "stopping": stopping, "destroyed": destroyed}


def tick():
    with Session() as s:
        t = now()
        for n in s.query(Node).filter(Node.status == "online", Node.last_seen < t - settings.node_timeout):
            n.status = "offline"
            s.query(Job).filter_by(node=n.id, status="running").update({"status": "lost", "finished": t})
        s.commit()
        for inst in list(s.query(Instance).filter_by(status="up")):
            env, node = s.get(Env, inst.env), s.query(Node).filter_by(name=inst.name).first()
            busy = node and s.query(Job).filter_by(node=node.id, status="running").count()
            expired = inst.expires and inst.expires < t
            idle = node and not busy and env and env.idle and t - node.busy_at > env.idle
            orphan = not node and t - inst.created > NEVER_JOINED
            if expired or idle or orphan:
                destroy(s, inst)
