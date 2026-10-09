"""Server settings: defaults < ~/.pyssion/server/server.json < PYSSION_<KEY> env vars."""
import os
from types import SimpleNamespace

from ..common import config

DEFAULTS = dict(
    public_url="http://127.0.0.1:8470", host="0.0.0.0", port=8470, data=str(config.HOME / "server"),
    db_url="", secret="", node_timeout=90,
    storage="local", s3_endpoint="", s3_access="", s3_secret="", s3_bucket="pyssion", s3_region="", s3_secure=True,
)


def _cast(default, value):
    if isinstance(default, bool):
        return str(value).lower() in ("1", "true", "yes", "on")
    return type(default)(value) if default is not None else value


def load():
    raw = {**DEFAULTS, **config.load("server/server.json")}
    return SimpleNamespace(**{k: _cast(DEFAULTS.get(k, ""), os.getenv(f"PYSSION_{k.upper()}", v)) for k, v in raw.items()})


settings = load()
