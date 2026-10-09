import json
import shutil
import subprocess


def available():
    return shutil.which("docker") is not None


def start(spec, code, env, gpu_ids, python):
    cmd = ["docker", "run", "--rm", "--name", f"pyssion-{env['PYSSION_JOB_ID']}", "-v", f"{code}:/work", "-w", "/work",
           "-v", f"{env['PYTHONPATH']}:/opt/pyssion/lib:ro", "-e", "PYTHONPATH=/opt/pyssion/lib"]
    if gpu_ids:
        cmd += ["--gpus", f'"device={",".join(map(str, gpu_ids))}"']
    for k in env:
        if k.startswith("PYSSION_") or k == "PYTHONUNBUFFERED":
            cmd += ["-e", k]
    cmd += [spec.get("image") or "python:3.11-slim", "python", "-m", "pyssion.agent.launch", "python", json.dumps(spec)]
    return subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def stop(proc, job_id):
    subprocess.run(["docker", "stop", f"pyssion-{job_id}"], capture_output=True)
