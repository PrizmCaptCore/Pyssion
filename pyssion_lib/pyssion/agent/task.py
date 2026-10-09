import os
import shutil
import threading
import time
import traceback
from pathlib import Path

from ..common import config, download, unpack
from . import executor
from .sync import Outputs

_runtime_lock = threading.Lock()


def runtime_dir():
    """A copy of just the `pyssion` package, put on the job's PYTHONPATH so jobs can import it."""
    dest = config.HOME / "runtime"
    with _runtime_lock:
        if not (dest / "pyssion").exists():
            src = Path(__file__).resolve().parents[1]
            shutil.copytree(src, dest / "pyssion", ignore=shutil.ignore_patterns("__pycache__", "manager", "legacy"))
    return dest


class Task(threading.Thread):
    def __init__(self, agent, claim, gpu_ids):
        super().__init__(daemon=True)
        self.agent, self.job, self.gpu_ids = agent, claim["job"], gpu_ids
        self.id, self.spec = self.job["id"], self.job["spec"]
        self.code_url, self.token = claim["code_url"], claim["token"]
        self.proc, self.cancelled = None, False
        self.buf, self.lock = [], threading.Lock()

    def log(self, text):
        with self.lock:
            self.buf.append(text)

    def flush(self):
        with self.lock:
            text, self.buf = "".join(self.buf), []
        if text:
            try:
                self.agent.api.post(f"/v1/nodes/jobs/{self.id}/logs", json={"text": text})
            except OSError:
                with self.lock:
                    self.buf.insert(0, text)

    def cancel(self):
        self.cancelled = True
        if self.proc and self.proc.poll() is None:
            executor.stop(self.spec, self.proc, self.id)

    def env(self):
        e = {k: v for k, v in os.environ.items() if not k.startswith("PYSSION_")}
        e.update(PYSSION_JOB_ID=self.id, PYSSION_GROUP=self.job["group"], PYSSION_RANK=str(self.job["rank"]),
                 PYSSION_WORLD_SIZE=str(self.job["world"]), PYSSION_SERVER=self.agent.server,
                 PYSSION_TOKEN=self.token, PYTHONPATH=str(runtime_dir()), PYTHONUNBUFFERED="1",
                 CUDA_VISIBLE_DEVICES=",".join(map(str, self.gpu_ids)))
        return e

    def _pump(self):
        for chunk in iter(lambda: self.proc.stdout.read1(65536), b""):
            self.log(chunk.decode("utf-8", "replace"))

    def run(self):
        wd = self.agent.workdir / self.id
        code, rc = wd / "code", -1
        outputs = Outputs(self.agent.api, self.id, code / (self.spec.get("outputs") or "outputs"), self.log)
        try:
            unpack(download(self.code_url, wd / "code.tar.gz"), code)
            if not self.cancelled:
                self.proc = executor.start(self.spec, code, self.env(), self.gpu_ids, self.agent.python)
                pump = threading.Thread(target=self._pump, daemon=True)
                pump.start()
                ticks = 0
                while self.proc.poll() is None:
                    time.sleep(2)
                    self.flush()
                    ticks += 1
                    if ticks % 15 == 0:
                        outputs.sync()
                rc = self.proc.returncode
                pump.join(timeout=10)
        except Exception:
            self.log(traceback.format_exc())
        finally:
            uploaded = outputs.sync(final=True)
            self.log(f"[pyssion] exit code {rc}\n")
            self.flush()
            self._finish(rc)
            if uploaded:
                shutil.rmtree(wd, ignore_errors=True)
            else:
                print(f"[agent] job {self.id}: outputs kept at {wd} (upload failed)", flush=True)

    def _finish(self, rc):
        for _ in range(60):
            try:
                return self.agent.api.post(f"/v1/nodes/jobs/{self.id}/finish", json={"exit_code": rc})
            except OSError:
                time.sleep(10)
