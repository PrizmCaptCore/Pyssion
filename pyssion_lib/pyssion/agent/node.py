import os
import shutil
import socket
import subprocess
import sys
import time

from ..common import Api, config
from .executor import available
from .task import Task


def detect_gpus():
    try:
        out = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return 0
    return sum(l.startswith("GPU ") for l in out.splitlines())


def default_python():
    """Interpreter for jobs: the host's python (with its preinstalled torch), not the agent's."""
    if os.name == "nt":
        return sys.executable
    return shutil.which("python3") or shutil.which("python") or sys.executable


class Agent:
    def __init__(self, server, join=None, name=None, env="default", gpus=None, max_jobs=None,
                 orphan_cmd=None, orphan_after=600, python=None):
        self.server = server.rstrip("/")
        self.gpus = detect_gpus() if gpus is None else gpus
        self.max_jobs = max_jobs or max(1, self.gpus)
        self.orphan_cmd, self.orphan_after = orphan_cmd, orphan_after
        self.python = python or default_python()
        self.workdir = config.HOME / "work"
        self.tasks = {}
        state = config.load("agent.json")
        if state.get("server") != self.server or not state.get("token"):
            if not join:
                raise RuntimeError("This node has not joined yet: pass --join <token>.")
            r = Api(self.server, "").post("/v1/nodes/join", json=dict(
                token=join, name=name or socket.gethostname(), env=env, gpus=self.gpus, executors=available()))
            state = {"server": self.server, "node": r["node"], "token": r["token"], "env": r["env"]}
            config.save("agent.json", state)
        self.node, self.api = state["node"], Api(self.server, state["token"])

    def run(self):
        print(f"[agent] node {self.node} -> {self.server} | {self.gpus} GPU | executors {available()}", flush=True)
        last_ok = time.time()
        while True:
            self.tasks = {k: t for k, t in self.tasks.items() if t.is_alive()}
            try:
                hb = self.api.post("/v1/nodes/heartbeat", json={"running": list(self.tasks)})
                last_ok = time.time()
            except OSError as e:
                print(f"[agent] manager unreachable: {e}", flush=True)
                if not self.tasks and time.time() - last_ok > self.orphan_after:
                    return self.orphan()
                time.sleep(10)
                continue
            for jid in hb["cancel"]:
                if jid in self.tasks:
                    self.tasks[jid].cancel()
            if hb["shutdown"]:
                print("[agent] removed by manager; stopping", flush=True)
                for t in self.tasks.values():
                    t.cancel()
                return
            if len(self.tasks) < self.max_jobs:
                self.claim()
            time.sleep(3)

    def claim(self):
        free = sorted(set(range(self.gpus)) - {g for t in self.tasks.values() for g in t.gpu_ids})
        r = self.api.post("/v1/nodes/claim", json={"gpus": len(free), "executors": available()})
        if r["job"]:
            t = Task(self, r, free[: r["job"]["spec"]["gpus"]])
            self.tasks[t.id] = t
            print(f"[agent] job {t.id} started (gpus {t.gpu_ids})", flush=True)
            t.start()

    def orphan(self):
        print("[agent] orphaned: manager gone and no jobs left", flush=True)
        if self.orphan_cmd:
            subprocess.run(self.orphan_cmd, shell=True)
