"""The manager hands out its own agent, so a new node needs only curl + python3 to join.

    curl -fsSL http://MANAGER:8470/agent/install.sh | sh -s -- <join-token>
"""
import io
import tarfile
from functools import cache
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response

from ..settings import settings

router = APIRouter(prefix="/agent")
PKG = Path(__file__).resolve().parents[2]
SKIP = ("__pycache__", "pyssion/manager", "pyssion/legacy")

INSTALL = r"""#!/bin/sh
# usage: curl -fsSL @SERVER@/agent/install.sh | sh -s -- JOIN_TOKEN [--foreground] [agent options]
set -e
SERVER="@SERVER@"; TOKEN="$1"; shift || true
DIR="${PYSSION_HOME:-/opt/pyssion}"; mkdir -p "$DIR/lib" 2>/dev/null || DIR="$HOME/.pyssion"; mkdir -p "$DIR/lib"
curl -fsSL "$SERVER/agent/pyssion.tar.gz" | tar -xz -C "$DIR/lib"
PY="$(command -v python3 || command -v python)"
[ "$(id -u)" = 0 ] && command -v useradd >/dev/null && { id pyssion >/dev/null 2>&1 || useradd -r -m pyssion; }
ENVS="PYTHONPATH=$DIR/lib PYSSION_HOME=$DIR PYSSION_NODE_NAME=${PYSSION_NODE_NAME:-$(hostname)}"
CMD="$PY -m pyssion agent --server $SERVER --join $TOKEN $*"
case " $* " in *" --foreground "*) exec env $ENVS PYSSION_ORPHAN_CMD="$PYSSION_ORPHAN_CMD" $CMD ;; esac
if [ "$(id -u)" = 0 ] && command -v systemctl >/dev/null; then
  cat > /etc/systemd/system/pyssion-agent.service <<UNIT
[Unit]
Description=Pyssion agent
After=network-online.target
[Service]
Environment=$ENVS
Environment="PYSSION_ORPHAN_CMD=$PYSSION_ORPHAN_CMD"
ExecStart=$CMD
Restart=on-failure
[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload && systemctl enable --now pyssion-agent
else
  env $ENVS PYSSION_ORPHAN_CMD="$PYSSION_ORPHAN_CMD" nohup $CMD >> "$DIR/agent.log" 2>&1 &
fi
echo "pyssion agent started -> $SERVER"
"""


@cache
def _bundle():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(PKG, arcname="pyssion", filter=lambda ti: None if any(s in ti.name for s in SKIP) else ti)
    return buf.getvalue()


@router.get("/pyssion.tar.gz")
def bundle():
    return Response(_bundle(), media_type="application/gzip")


@router.get("/install.sh")
def install():
    return PlainTextResponse(INSTALL.replace("@SERVER@", settings.public_url.rstrip("/")))
