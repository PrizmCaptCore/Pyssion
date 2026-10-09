"""Project archive in/out, honoring .pyssionignore."""
import fnmatch
import tarfile
from pathlib import Path, PurePosixPath

DEFAULT_IGNORE = [".git/", "__pycache__/", ".venv/", "venv/", ".pyssion*", "pyssion_results/", "*.pyc"]


def ignore_patterns(root):
    f = Path(root) / ".pyssionignore"
    lines = f.read_text(encoding="utf-8").splitlines() if f.exists() else []
    return DEFAULT_IGNORE + [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]


def ignored(rel, patterns):
    for p in patterns:
        if p.endswith("/"):
            if f"/{p}" in f"/{rel}/":
                return True
        elif fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(PurePosixPath(rel).name, p):
            return True
    return False


def pack(root, dest):
    root, pats = Path(root), ignore_patterns(root)
    with tarfile.open(dest, "w:gz") as tar:
        for f in sorted(root.rglob("*")):
            rel = f.relative_to(root).as_posix()
            if f.is_file() and not ignored(rel, pats):
                tar.add(f, arcname=rel)
    return dest


def unpack(src, dest):
    with tarfile.open(src) as tar:
        for m in tar.getmembers():
            if m.name.startswith("/") or ".." in PurePosixPath(m.name).parts or not (m.isfile() or m.isdir()):
                raise ValueError(f"unsafe archive member: {m.name}")
        tar.extractall(dest, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
    return Path(dest)
