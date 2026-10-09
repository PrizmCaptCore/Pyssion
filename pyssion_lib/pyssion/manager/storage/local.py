"""Files on the manager's disk, served by the manager itself through HMAC-signed URLs."""
import hashlib
import hmac
import time
from pathlib import Path
from urllib.parse import quote


class LocalStorage:
    def __init__(self, s):
        self.root = (Path(s.data) / "blobs").resolve()
        self.url, self.key = s.public_url.rstrip("/"), s.secret.encode()

    def _sign(self, key, method, exp):
        return hmac.new(self.key, f"{method}:{key}:{exp}".encode(), hashlib.sha256).hexdigest()

    def presign(self, key, method="GET", expires=3600):
        exp = int(time.time()) + expires
        return f"{self.url}/blob/{quote(key)}?m={method}&e={exp}&s={self._sign(key, method, exp)}"

    def verify(self, key, method, exp, sig):
        return exp > time.time() and hmac.compare_digest(sig, self._sign(key, method, exp))

    def path(self, key):
        p = (self.root / key).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError(key)
        return p

    def list(self, prefix):
        base = self.path(prefix.rsplit("/", 1)[0]) if "/" in prefix else self.root
        if not base.is_dir():
            return []
        keys = (f.relative_to(self.root).as_posix() for f in base.rglob("*") if f.is_file())
        return sorted(k for k in keys if k.startswith(prefix))
