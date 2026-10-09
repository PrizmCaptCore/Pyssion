import time
from pathlib import Path, PurePosixPath

from ..common import download

DONE = {"succeeded", "failed", "cancelled", "lost"}


class Job:
    def __init__(self, api, job_id):
        self.api, self.id = api, job_id

    def status(self):
        return self.api.get(f"/v1/jobs/{self.id}")

    def logs(self, follow=True):
        offset = 0
        while True:
            r = self.api.get(f"/v1/jobs/{self.id}/logs", offset=offset)
            print(r["text"], end="", flush=True)
            offset = r["offset"]
            if r["text"]:
                continue
            if not follow or r["status"] in DONE:
                return r["status"]
            time.sleep(2)

    def fetch(self, dest=None):
        dest = Path(dest or Path("pyssion_results") / self.id)
        files = self.api.get(f"/v1/jobs/{self.id}/outputs")["files"]
        for f in files:
            if ".." not in PurePosixPath(f["path"]).parts:
                download(f["url"], dest / f["path"])
        print(f"[pyssion] {self.id}: {len(files)} file(s) -> {dest}")
        return dest

    def cancel(self):
        return self.api.post(f"/v1/jobs/{self.id}/cancel")

    def wait(self, fetch=True):
        status = self.logs()
        print(f"[pyssion] {self.id}: {status}")
        if fetch:
            self.fetch()
        return status
