"""Local record of submitted jobs, so a dropped session can re-attach."""
import time

from ..common import config


def add(server, job_id, entrypoint):
    h = config.load("jobs.json", [])
    h.append({"id": job_id, "server": server, "entrypoint": entrypoint, "at": time.time()})
    config.save("jobs.json", h[-500:])


def entries():
    return config.load("jobs.json", [])
