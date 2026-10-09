"""Local state under PYSSION_HOME (default ~/.pyssion)."""
import json
import os
from pathlib import Path

HOME = Path(os.getenv("PYSSION_HOME", Path.home() / ".pyssion"))


def load(name, default=None):
    p = HOME / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else ({} if default is None else default)


def save(name, data):
    p = HOME / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return p


def client_config():
    """Manager URL + token. Env vars win, then PYSSION_CONFIG file, then ~/.pyssion/client.json."""
    f = os.getenv("PYSSION_CONFIG")
    cfg = json.loads(Path(f).read_text(encoding="utf-8")) if f else load("client.json")
    url, token = os.getenv("PYSSION_SERVER", cfg.get("server")), os.getenv("PYSSION_TOKEN", cfg.get("token"))
    if not url or not token:
        raise RuntimeError("No Pyssion manager configured. Run `pyssion init` or `pyssion login`.")
    return url.rstrip("/"), token
