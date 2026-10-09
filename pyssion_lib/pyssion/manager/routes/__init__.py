"""HTTP API, one module per caller: users (jobs), nodes, admins, reactor store, blobs, agent distribution."""
from . import admin, blob, dist, jobs, nodes, store

ROUTERS = [m.router for m in (jobs, nodes, admin, store, blob, dist)]

__all__ = ["ROUTERS"]
