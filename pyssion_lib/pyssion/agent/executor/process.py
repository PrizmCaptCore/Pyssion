import json
import os
import subprocess
import sys


def available():
    return True


def _job_user(code):
    """When the agent runs as root, run jobs as the unprivileged `pyssion` user so they cannot read the node token."""
    if os.name == "nt" or os.geteuid() != 0:
        return None
    import pwd
    try:
        u = pwd.getpwnam("pyssion")
    except KeyError:
        return None
    for root, dirs, files in os.walk(code.parent):
        for p in [root, *(os.path.join(root, n) for n in dirs + files)]:
            os.chown(p, u.pw_uid, u.pw_gid)
    return u


def start(spec, code, env, gpu_ids, python):
    kw, u = {}, _job_user(code)
    if u:
        kw, env["HOME"] = {"user": u.pw_uid, "group": u.pw_gid, "extra_groups": []}, u.pw_dir
    return subprocess.Popen([sys.executable, "-m", "pyssion.agent.launch", python, json.dumps(spec)],
                            cwd=code, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)


def stop(proc, job_id):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.terminate()
