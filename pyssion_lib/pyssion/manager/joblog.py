"""Job and provisioning logs as append-only files in the server data dir."""
from pathlib import Path

from .settings import settings


def log_path(name):
    p = Path(settings.data) / "logs" / f"{name}.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def append(name, text):
    with open(log_path(name), "a", encoding="utf-8", newline="") as f:
        f.write(text)


def read(name, offset, size=1 << 20):
    p = log_path(name)
    if not p.exists():
        return "", offset
    with open(p, "rb") as f:
        f.seek(offset)
        data = f.read(size)
    return data.decode("utf-8", "replace"), offset + len(data)
