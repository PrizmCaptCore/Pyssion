import os
import threading
import time

from .aggregator import Aggregator
from .store import Store, dumps, loads


class Worker:
    """Push local weights each round and pull the aggregated global weights.

    Defaults come from the job env, so `pyssion run train.py --replicas 4` just works:
    the replicas share a session, and rank 0 also hosts the aggregator.
    """

    def __init__(self, session=None, worker_id=None, aggregate=None, poll=5, timeout=3600):
        self.store = Store(session)
        self.id = str(worker_id if worker_id is not None else os.getenv("PYSSION_RANK", "0"))
        self.poll, self.timeout, self.round = poll, timeout, 0
        if self.id == "0" if aggregate is None else aggregate:
            threading.Thread(target=Aggregator(session).run, daemon=True).start()

    def push(self, state_dict, n_samples=1):
        state = {k: v.detach().cpu() for k, v in state_dict.items()}
        self.store.put(f"updates/{self.round:06d}/{self.id}.pt", dumps({"n": n_samples, "state": state}))

    def pull(self):
        key, start = f"global/{self.round:06d}.pt", time.time()
        while key not in self.store.keys("global/"):
            if time.time() - start > self.timeout:
                raise TimeoutError(f"no global state for round {self.round}")
            time.sleep(self.poll)
        self.round += 1
        return loads(self.store.get(key))

    def step(self, model, n_samples=1):
        """push + pull + load, for the common case."""
        self.push(model.state_dict(), n_samples)
        model.load_state_dict(self.pull())
        return model
