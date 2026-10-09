import io
import os

from ..common import Api, config, request


def session_id():
    return os.getenv("PYSSION_GROUP") or "default"


class Store:
    """Blob store scoped to reactor/<session>/ on the manager's storage."""

    def __init__(self, session=None):
        url, token = config.client_config()
        self.api, self.prefix = Api(url, token), f"reactor/{session or session_id()}/"

    def _url(self, key, method):
        return self.api.post("/v1/store/url", json={"key": self.prefix + key, "method": method})["url"]

    def put(self, key, data):
        request("PUT", self._url(key, "PUT"), data, timeout=3600)

    def get(self, key):
        return request("GET", self._url(key, "GET"), timeout=3600, raw=True)

    def keys(self, sub=""):
        keys = self.api.get("/v1/store/list", prefix=self.prefix + sub)["keys"]
        return [k[len(self.prefix):] for k in keys]


def dumps(obj):
    import torch
    buf = io.BytesIO()
    torch.save(obj, buf)
    return buf.getvalue()


def loads(data):
    import torch
    return torch.load(io.BytesIO(data), map_location="cpu", weights_only=True)
