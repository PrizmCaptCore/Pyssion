"""pyssion <command>. Options go before positionals: `pyssion run --gpus 1 train.py --lr 0.1`."""
import argparse
import json
import os
import sys


def _api():
    from .common import Api, config
    return Api(*config.client_config())


def _show(x):
    print(json.dumps(x, indent=2, default=str))


def _parser():
    p = argparse.ArgumentParser(prog="pyssion", description="Pack your code, ignite it anywhere.")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("init", help="ignite: manager + local agent + hello-world on this machine")
    c.add_argument("--public-url", help="URL nodes use to reach this manager")
    c.add_argument("--port", type=int, default=8470)
    c.add_argument("--db-url", default="", help="SQLAlchemy URL, e.g. postgresql+psycopg://...")
    c.add_argument("--no-start", action="store_true")
    c.add_argument("--no-hello", action="store_true")
    sub.add_parser("stop", help="stop the manager and agent started by init")
    sub.add_parser("server", help="run the manager in the foreground")

    c = sub.add_parser("agent", help="run a node agent in the foreground")
    c.add_argument("--server", default=os.getenv("PYSSION_SERVER") or None)
    c.add_argument("--join", default=os.getenv("PYSSION_JOIN_TOKEN") or None)
    c.add_argument("--name", default=os.getenv("PYSSION_NODE_NAME") or None)
    c.add_argument("--env", default=os.getenv("PYSSION_ENV", "default"))
    c.add_argument("--gpus", type=int)
    c.add_argument("--max-jobs", type=int)
    c.add_argument("--python", help="interpreter for jobs (default: host python3)")
    c.add_argument("--orphan-cmd", default=os.getenv("PYSSION_ORPHAN_CMD") or None)
    c.add_argument("--orphan-after", type=float, default=600)
    c.add_argument("--foreground", action="store_true", help=argparse.SUPPRESS)

    c = sub.add_parser("login", help="save manager URL + token for this machine")
    c.add_argument("--server", required=True)
    c.add_argument("--token", required=True)

    c = sub.add_parser("run", help="ship a project dir and run ENTRYPOINT on a node")
    c.add_argument("--dir", default=".")
    c.add_argument("--req", help="requirements file inside the project")
    c.add_argument("--gpus", type=int, default=0)
    c.add_argument("--env", help="only run on nodes of this env")
    c.add_argument("--replicas", type=int, default=1)
    c.add_argument("--executor", default="process", choices=["process", "container"])
    c.add_argument("--image", help="container image (container executor)")
    c.add_argument("--outputs", default="outputs")
    c.add_argument("--detach", action="store_true")
    c.add_argument("entrypoint")
    c.add_argument("args", nargs=argparse.REMAINDER)

    for name in ("status", "logs", "fetch", "cancel"):
        c = sub.add_parser(name, help=f"{name} a job")
        c.add_argument("job")
        if name == "fetch":
            c.add_argument("--dest")
    sub.add_parser("jobs", help="list jobs")
    sub.add_parser("history", help="jobs submitted from this machine")
    sub.add_parser("nodes", help="list nodes (admin)")

    c = sub.add_parser("token", help="issue a token (admin)")
    c.add_argument("--kind", default="user", choices=["user", "join", "admin"])
    c.add_argument("--env", default="", help="join tokens: env the node will belong to")
    c.add_argument("--uses", type=int)
    c.add_argument("--ttl", type=float, help="seconds")

    c = sub.add_parser("env", help="manage environments (admin)")
    es = c.add_subparsers(dest="action", required=True)
    e = es.add_parser("set")
    e.add_argument("name")
    e.add_argument("--provisioner", default="manual", choices=["manual", "terraform", "runpod"])
    e.add_argument("--config", default="{}", help='JSON, e.g. \'{"module": "aws", "vars": {"region": "us-west-2"}}\'')
    e.add_argument("--max-nodes", type=int, default=1)
    e.add_argument("--ttl", type=float, default=0)
    e.add_argument("--idle", type=float, default=1800)
    e = es.add_parser("up")
    e.add_argument("name")
    e.add_argument("--count", type=int, default=1)
    es.add_parser("down").add_argument("name")
    es.add_parser("list")

    sub.add_parser("kill", help="cancel every job and destroy every provisioned node (admin)")
    return p


def main(argv=None):
    try:
        _main(_parser().parse_args(argv))
    except (OSError, RuntimeError) as e:
        sys.exit(f"pyssion: {e}")
    except KeyboardInterrupt:
        sys.exit(130)


def _main(a):
    if a.cmd == "init":
        from .bootstrap import init
        return init(a.public_url, a.port, a.db_url, start=not a.no_start, hello=not a.no_hello)
    if a.cmd == "stop":
        from .bootstrap import stop
        return stop()
    if a.cmd == "server":
        from .manager import serve
        return serve()
    if a.cmd == "agent":
        from .agent import Agent
        from .common import config
        server = a.server or config.load("agent.json").get("server")
        if not server:
            sys.exit("pyssion agent: --server is required on first start")
        return Agent(server, a.join, a.name, a.env, a.gpus, a.max_jobs, a.orphan_cmd, a.orphan_after, a.python).run()
    if a.cmd == "login":
        from .common import config
        config.save("client.json", {"server": a.server.rstrip("/"), "token": a.token})
        return print(f"[pyssion] logged in to {a.server}")
    if a.cmd == "run":
        from .client import Pyssion
        jobs = Pyssion(project_dir=a.dir).run(a.entrypoint, a.args, a.req, a.gpus, a.env, a.outputs, a.executor,
                                              a.image, a.replicas, wait=not a.detach)
        if not a.detach:
            sys.exit(0 if all(j.status()["status"] == "succeeded" for j in jobs) else 1)
        return
    if a.cmd in ("status", "logs", "fetch", "cancel"):
        from .client import Job
        job = Job(_api(), a.job)
        return {"status": lambda: _show(job.status()), "logs": job.logs,
                "fetch": lambda: job.fetch(a.dest), "cancel": lambda: _show(job.cancel())}[a.cmd]()
    if a.cmd == "history":
        from .client import history
        return _show(history.entries())
    api = _api()
    if a.cmd == "jobs":
        for j in api.get("/v1/jobs"):
            print(f"{j['id']}  {j['status']:<10} {j['spec']['entrypoint']:<24} node={j['node']}")
    elif a.cmd == "nodes":
        for n in api.get("/v1/nodes"):
            print(f"{n['id']}  {n['status']:<8} {n['name']:<24} env={n['env']} gpus={n['gpus']}")
    elif a.cmd == "token":
        t = api.post("/v1/tokens", json={"kind": a.kind, "subject": a.env, "uses": a.uses, "ttl": a.ttl})["token"]
        print(t)
        if a.kind == "join":
            print(f"\nLinux node:   curl -fsSL {api.url}/agent/install.sh | sh -s -- {t}"
                  f"\nAny machine:  pyssion agent --server {api.url} --join {t}")
    elif a.cmd == "env":
        if a.action == "set":
            _show(api.call("PUT", f"/v1/envs/{a.name}", json_=dict(
                provisioner=a.provisioner, config=json.loads(a.config), max_nodes=a.max_nodes, ttl=a.ttl, idle=a.idle)))
        elif a.action == "list":
            _show(api.get("/v1/envs"))
        else:
            path = f"/v1/envs/{a.name}/{a.action}" + (f"?count={a.count}" if a.action == "up" else "")
            _show(api.post(path))
    elif a.cmd == "kill":
        _show(api.post("/v1/kill"))


if __name__ == "__main__":
    main()
