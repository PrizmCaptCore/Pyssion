import os
import time

from .store import Store, dumps, loads


class Aggregator:
    """Per round: wait for worker updates, publish their sample-weighted average as the global state."""

    def __init__(self, session=None, min_workers=None, timeout=600, poll=5):
        self.store = Store(session)
        self.min = min_workers or int(os.getenv("PYSSION_WORLD_SIZE", "1"))
        self.timeout, self.poll = timeout, poll

    def run(self, rounds=None):
        r = 0
        while rounds is None or r < rounds:
            self.aggregate(r)
            r += 1

    def aggregate(self, r):
        prefix, start = f"updates/{r:06d}/", time.time()
        while True:
            keys = self.store.keys(prefix)
            if len(keys) >= self.min or (keys and time.time() - start > self.timeout):
                break
            time.sleep(self.poll)
        total, acc, dtypes = 0, {}, {}
        for k in keys:
            u = loads(self.store.get(k))
            total += u["n"]
            for name, v in u["state"].items():
                dtypes[name] = v.dtype
                acc[name] = acc.get(name, 0) + v.float() * u["n"]
        avg = {name: (v / total).to(dtypes[name]) for name, v in acc.items()}
        self.store.put(f"global/{r:06d}.pt", dumps(avg))
        print(f"[reactor] round {r}: {len(keys)} update(s), {total} sample(s)", flush=True)
        return avg
