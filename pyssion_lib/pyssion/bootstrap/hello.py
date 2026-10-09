import tempfile
from pathlib import Path

from ..client import Pyssion

HELLO = """import os, platform
os.makedirs("outputs", exist_ok=True)
msg = f"hello from {platform.node()} (job {os.environ['PYSSION_JOB_ID']})"
print(msg)
open("outputs/hello.txt", "w").write(msg + "\\n")
"""


def hello():
    """Round trip through the whole system: pack -> upload -> node runs it -> logs -> outputs back here."""
    with tempfile.TemporaryDirectory() as d:
        Path(d, "hello.py").write_text(HELLO)
        return Pyssion(project_dir=d).run("hello.py")
