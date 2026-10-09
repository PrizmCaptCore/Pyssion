"""One working dir (and state) per machine, so apply/destroy never contend for a lock.

env.config = {"module": "aws" | "gcp" | "azure" | "nhn" | <any module source>, "vars": {...}}
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

from ..joblog import log_path
from ..settings import settings

MODULES = Path(__file__).parent / "modules"


class Terraform:
    def __init__(self, env):
        self.env, self.cfg = env, env.config or {}
        self.bin = shutil.which("tofu") or shutil.which("terraform")
        if not self.bin:
            raise ValueError("neither `tofu` nor `terraform` is installed on the manager host")

    def _dir(self, name):
        return Path(settings.data) / "tf" / self.env.name / name

    def _run(self, wd, *args):
        with open(log_path(f"provision-{wd.name}"), "a") as log:
            subprocess.run([self.bin, f"-chdir={wd}", *args, "-input=false", "-no-color"],
                           stdout=log, stderr=subprocess.STDOUT, check=True)

    def up(self, name, server_url, join_token):
        wd = self._dir(name)
        shutil.copytree(MODULES, wd / "modules", dirs_exist_ok=True)
        mod = self.cfg.get("module", "aws")
        node = {"source": f"./modules/{mod}" if (MODULES / mod).is_dir() else mod,
                "name": name, "server_url": server_url, "join_token": join_token, **self.cfg.get("vars", {})}
        main = {"module": {"node": node}, "output": {"id": {"value": "${module.node.id}"}}}
        if settings.db_url.startswith("postgres"):
            conn = re.sub(r"^postgres(ql)?(\+\w+)?://", "postgres://", settings.db_url)
            main["terraform"] = {"backend": {"pg": {"conn_str": conn, "schema_name": "tf_" + name.replace("-", "_")}}}
        (wd / "main.tf.json").write_text(json.dumps(main, indent=2))
        self._run(wd, "init")
        self._run(wd, "apply", "-auto-approve")
        return name

    def down(self, ref):
        wd = self._dir(ref)
        if wd.exists():
            self._run(wd, "destroy", "-auto-approve")
            shutil.rmtree(wd)
