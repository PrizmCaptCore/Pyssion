import time

from ..common import upload


class Outputs:
    """Uploads new or changed files under the job's outputs dir, so results survive the node."""

    def __init__(self, api, job_id, root, log):
        self.api, self.id, self.root, self.log, self.seen = api, job_id, root, log, {}

    def sync(self, final=False):
        if not self.root.is_dir():
            return True
        changed = {}
        for f in self.root.rglob("*"):
            if not f.is_file():
                continue
            st = f.stat()
            rel, sig = f.relative_to(self.root).as_posix(), (st.st_size, st.st_mtime_ns)
            if self.seen.get(rel) != sig and (final or time.time() - st.st_mtime > 5):
                changed[rel] = (f, sig)
        if not changed:
            return True
        try:
            urls = self.api.post(f"/v1/nodes/jobs/{self.id}/upload", json={"paths": list(changed)})["urls"]
            for rel, (f, sig) in changed.items():
                upload(urls[rel], f)
                self.seen[rel] = sig
            return True
        except OSError as e:
            self.log(f"[pyssion] output upload failed: {e}\n")
            return False
