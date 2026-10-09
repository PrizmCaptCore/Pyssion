import os
import secrets
import signal
import socket
import subprocess
import sys
import time
import urllib.request

from ..common import config


def lan_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def healthy(url, wait=0):
    for _ in range(max(1, wait * 2)):
        try:
            urllib.request.urlopen(url + "/health", timeout=2)
            return True
        except OSError:
            time.sleep(0.5)
    return False


def spawn(name, *args):
    log = config.HOME / f"{name}.log"
    kw = {"creationflags": 0x00000008 | 0x00000200} if os.name == "nt" else {"start_new_session": True}
    p = subprocess.Popen([sys.executable, "-m", "pyssion", *args], stdout=open(log, "a"), stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, **kw)
    config.save("pids.json", {**config.load("pids.json"), name: p.pid})
    print(f"[pyssion] {name} started (pid {p.pid}, log {log})")


def init(public_url=None, port=8470, db_url="", start=True, hello=True):
    server = config.load("server/server.json")
    fresh = not server.get("secret")
    server.setdefault("secret", secrets.token_hex(32))
    server.setdefault("port", port)
    server["public_url"] = public_url or server.get("public_url") or f"http://{lan_ip()}:{server['port']}"
    if db_url:
        server["db_url"] = db_url
    config.save("server/server.json", server)
    url, join = server["public_url"], None

    from ..manager import db
    from ..manager.auth import issue
    db.init()
    if fresh:
        with db.Session() as s:
            admin, join = issue(s, "admin", "admin"), issue(s, "join", "default", uses=1, ttl=3600)
        config.save("client.json", {"server": url, "token": admin})
        print(f"[pyssion] manager initialized at {url}\n[pyssion] admin credentials -> {config.HOME / 'client.json'}")
    else:
        print(f"[pyssion] manager already initialized at {url}")
    if url.startswith(("http://127.", "http://localhost")):
        print("[pyssion] note: other machines cannot reach this URL; pass --public-url to spread beyond this host")
    if not start:
        print("[pyssion] start with: pyssion server  (and on each node: pyssion agent --server URL --join TOKEN)")
        return
    if not healthy(url):
        spawn("server", "server")
        if not healthy(url, wait=30):
            return print(f"[pyssion] manager did not come up; see {config.HOME / 'server.log'}")
    if join or config.load("agent.json").get("server") == url:
        spawn("agent", "agent", "--server", url, *(["--join", join] if join else []))
    if hello:
        from .hello import hello as run_hello
        run_hello()


def stop():
    for name, pid in config.load("pids.json").items():
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
            else:
                os.killpg(pid, signal.SIGTERM)
            print(f"[pyssion] stopped {name} (pid {pid})")
        except OSError:
            pass
    config.save("pids.json", {})
