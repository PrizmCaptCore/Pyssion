import asyncio
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import db, rods
from .routes import ROUTERS
from .settings import settings


async def _rod_loop():
    while True:
        try:
            await asyncio.to_thread(rods.tick)
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(15)


@asynccontextmanager
async def _lifespan(app):
    task = asyncio.create_task(_rod_loop())
    yield
    task.cancel()


def create_app():
    if not settings.secret:
        raise RuntimeError("Server not initialized: run `pyssion init` first.")
    db.init()
    app = FastAPI(title="Pyssion Manager", lifespan=_lifespan)
    for r in ROUTERS:
        app.include_router(r)
    app.get("/health")(lambda: {"ok": True})
    return app


def serve():
    import uvicorn
    uvicorn.run(create_app(), host=settings.host, port=settings.port)
