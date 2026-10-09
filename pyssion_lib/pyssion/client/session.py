import os
import sys
import tempfile
from pathlib import Path

from ..common import Api, config, pack, upload
from . import history
from .job import Job


def remote():
    """True when this process already runs as a Pyssion job on a node."""
    return bool(os.getenv("PYSSION_JOB_ID"))


def _main_dir():
    f = getattr(sys.modules.get("__main__"), "__file__", None)
    return Path(f).resolve().parent if f else Path.cwd()


class Pyssion:
    def __init__(self, project_dir=None, server=None, token=None):
        if remote():
            return
        url, tok = (server, token) if server and token else config.client_config()
        self.server, self.api = url, Api(url, tok)
        self.dir = Path(project_dir or _main_dir()).resolve()

    def run(self, entrypoint=None, args=(), requirements=None, gpus=0, env=None, outputs="outputs",
            executor="process", image=None, replicas=1, wait=True):
        """Ship the project and run `entrypoint` on matching nodes.

        Without an entrypoint the calling script ships itself; on the node this call returns None
        so the script continues, and locally the process exits once the remote run is done.
        """
        if remote():
            return None
        implicit = entrypoint is None
        if implicit:
            entrypoint = Path(sys.modules["__main__"].__file__).resolve().relative_to(self.dir).as_posix()
        if requirements is None and (self.dir / "requirements.txt").exists():
            requirements = "requirements.txt"
        spec = dict(entrypoint=entrypoint, args=[str(a) for a in args], requirements=requirements, gpus=gpus,
                    env=env, outputs=outputs, executor=executor, image=image, replicas=replicas)
        r = self.api.post("/v1/jobs", json=spec)
        with tempfile.TemporaryDirectory() as tmp:
            upload(r["upload_url"], pack(self.dir, Path(tmp) / "code.tar.gz"))
        self.api.post(f"/v1/jobs/start/{r['group']}")
        jobs = [Job(self.api, i) for i in r["jobs"]]
        for j in jobs:
            history.add(self.server, j.id, entrypoint)
        print(f"[pyssion] fission! group {r['group']} -> {', '.join(r['jobs'])}")
        if not wait:
            return jobs
        statuses = [j.wait() for j in jobs]
        if implicit:
            sys.exit(0 if all(s == "succeeded" for s in statuses) else 1)
        return jobs

    def attach(self, job_id):
        return Job(self.api, job_id)

    def jobs(self, limit=50):
        return self.api.get("/v1/jobs", limit=limit)
