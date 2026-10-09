"""How a job process is isolated on the node: plain process (default) or docker container."""
from . import container, process

EXECUTORS = {"process": process, "container": container}


def available():
    return [name for name, ex in EXECUTORS.items() if ex.available()]


def start(spec, code, env, gpu_ids, python):
    return EXECUTORS[spec.get("executor") or "process"].start(spec, code, env, gpu_ids, python)


def stop(spec, proc, job_id):
    EXECUTORS[spec.get("executor") or "process"].stop(proc, job_id)


__all__ = ["EXECUTORS", "available", "start", "stop"]
