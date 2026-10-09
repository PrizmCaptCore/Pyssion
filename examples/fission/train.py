"""Ships itself to a node, trains there, and the checkpoint comes back to ./pyssion_results/<job>/.

    python train.py
"""
import os

from pyssion import Pyssion

Pyssion().run(gpus=1)  # locally this never returns; on the node it is a no-op

import torch  # noqa: E402

device = "cuda" if torch.cuda.is_available() else "cpu"
model = torch.nn.Linear(16, 1).to(device)
opt = torch.optim.SGD(model.parameters(), lr=0.1)
for step in range(100):
    x = torch.randn(64, 16, device=device)
    loss = (model(x) - x.sum(1, keepdim=True)).pow(2).mean()
    opt.zero_grad()
    loss.backward()
    opt.step()
    if step % 20 == 0:
        print(f"step {step} loss {loss.item():.4f}", flush=True)

os.makedirs("outputs", exist_ok=True)
torch.save(model.state_dict(), "outputs/model.pt")
