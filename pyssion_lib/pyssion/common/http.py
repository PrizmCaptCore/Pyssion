"""Tiny urllib client so nodes and jobs need no third-party packages."""
import json
import os
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode


class ApiError(OSError):
    """Remote side answered with an HTTP error."""


def request(method, url, data=None, headers=None, timeout=30, raw=False):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return json.loads(body) if not raw and r.headers.get_content_type() == "application/json" else body
    except urllib.error.HTTPError as e:
        raise ApiError(f"{method} {url.split('?')[0]} -> {e.code}: {e.read().decode(errors='replace')}") from None


def upload(url, path):
    with open(path, "rb") as f:
        request("PUT", url, f, {"Content-Length": str(os.path.getsize(path))}, timeout=3600)


def download(url, dest):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=3600) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)
    return dest


class Api:
    def __init__(self, url, token):
        self.url, self.headers = url.rstrip("/"), {"Authorization": f"Bearer {token}"}

    def call(self, method, path, json_=None, params=None, retries=3):
        url = self.url + path + ("?" + urlencode(params) if params else "")
        headers, data = dict(self.headers), None
        if json_ is not None:
            data, headers["Content-Type"] = json.dumps(json_).encode(), "application/json"
        for i in range(retries):
            try:
                return request(method, url, data, headers)
            except ApiError:
                raise
            except OSError:
                if i == retries - 1:
                    raise
                time.sleep(2 ** i)

    def get(self, path, **params):
        return self.call("GET", path, params=params)

    def post(self, path, json=None):
        return self.call("POST", path, json_=json if json is not None else {})
