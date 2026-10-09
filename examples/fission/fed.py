"""Reactor: N replicas train on their own data shard and average weights every round.

    pyssion run --replicas 4 fed.py
"""
import os

import torch

from pyssion.reactor import Worker

rank, world = int(os.environ["PYSSION_RANK"]), int(os.environ["PYSSION_WORLD_SIZE"])
torch.manual_seed(rank)
model = torch.nn.Linear(16, 1)
opt = torch.optim.SGD(model.parameters(), lr=0.1)
worker = Worker()

for rnd in range(5):
    for _ in range(50):
        x = torch.randn(64, 16) + rank  # each replica sees a different distribution
        loss = (model(x) - x.sum(1, keepdim=True)).pow(2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    worker.step(model, n_samples=50 * 64)
    print(f"rank {rank}/{world} round {rnd} loss {loss.item():.4f}", flush=True)

if rank == 0:
    os.makedirs("outputs", exist_ok=True)
    torch.save(model.state_dict(), "outputs/global.pt")
