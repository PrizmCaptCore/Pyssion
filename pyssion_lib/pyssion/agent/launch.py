"""Runs inside the job: optional isolated env + requirements, then becomes the user's entrypoint."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def step(cmd):
    print("[pyssion] $", " ".join(map(str, cmd)), flush=True)
    subprocess.check_call(cmd)


def main(python, spec):
    python = shutil.which(python) or python
    req = spec.get("requirements")
    if req:
        venv, uv = Path(".venv"), shutil.which("uv")
        step([uv, "venv", "--system-site-packages", "-p", python, venv] if uv
             else [python, "-m", "venv", "--system-site-packages", venv])
        python = str((venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")).resolve())
        step([uv, "pip", "install", "-p", python, "-r", req] if uv else [python, "-m", "pip", "install", "-r", req])
    cmd = [python, "-u", spec["entrypoint"], *spec.get("args", [])]
    print("[pyssion] $", " ".join(cmd), flush=True)
    if os.name == "nt":
        sys.exit(subprocess.call(cmd))
    os.execv(cmd[0], cmd)


if __name__ == "__main__":
    main(sys.argv[1], json.loads(sys.argv[2]))
