"""SQLite by default (hello-world), Postgres via PYSSION_DB_URL for real use."""
import time
import uuid
from pathlib import Path

from sqlalchemy import JSON, Boolean, Column, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .settings import settings


def now():
    return time.time()


def new_id():
    return uuid.uuid4().hex[:12]


class Base(DeclarativeBase):
    def view(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Token(Base):
    __tablename__ = "tokens"
    hash = Column(String, primary_key=True)
    kind = Column(String)                      # admin | user | join | node | job
    subject = Column(String, default="")      # user name / env name / node id / job id
    uses = Column(Integer, nullable=True)     # remaining uses (join tokens)
    expires = Column(Float, nullable=True)


class Node(Base):
    __tablename__ = "nodes"
    id = Column(String, primary_key=True, default=new_id)
    name = Column(String)
    env = Column(String, default="default")
    gpus = Column(Integer, default=0)
    executors = Column(JSON, default=list)
    status = Column(String, default="online")  # online | offline | removed
    last_seen = Column(Float, default=now)
    busy_at = Column(Float, default=now)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, default=new_id)
    group = Column(String, index=True)
    rank = Column(Integer, default=0)
    owner = Column(String, default="")
    status = Column(String, default="pending")  # pending | queued | running | succeeded | failed | cancelled | lost
    spec = Column(JSON)
    node = Column(String, nullable=True)
    exit_code = Column(Integer, nullable=True)
    cancel = Column(Boolean, default=False)
    created = Column(Float, default=now)
    started = Column(Float, nullable=True)
    finished = Column(Float, nullable=True)


class Env(Base):
    """A place nodes come from. `manual` envs are joined by hand; others are provisioned."""
    __tablename__ = "envs"
    name = Column(String, primary_key=True)
    provisioner = Column(String, default="manual")  # manual | terraform | runpod
    config = Column(JSON, default=dict)
    max_nodes = Column(Integer, default=1)           # control rod: provisioned nodes alive at once
    ttl = Column(Float, default=0)                   # control rod: max node lifetime in seconds (0 = none)
    idle = Column(Float, default=1800)               # control rod: destroy after idle seconds (0 = never)


class Instance(Base):
    """A provisioned machine, tracked so control rods can destroy it."""
    __tablename__ = "instances"
    name = Column(String, primary_key=True)
    env = Column(String)
    ref = Column(String, nullable=True)
    status = Column(String, default="provisioning")  # provisioning | up
    created = Column(Float, default=now)
    expires = Column(Float, nullable=True)


_url = settings.db_url or f"sqlite:///{Path(settings.data) / 'pyssion.db'}"
engine = create_engine(_url, connect_args={"check_same_thread": False} if _url.startswith("sqlite") else {})
Session = sessionmaker(engine, expire_on_commit=False)


def init():
    Path(settings.data).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def get():
    with Session() as s:
        yield s
