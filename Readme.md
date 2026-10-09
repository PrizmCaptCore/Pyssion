# Pyssion

## 프로젝트 계승 · Project continuity

이 프로젝트는 제가 이전 GitHub 계정 **[CaptCore](https://github.com/CaptCore)**에서 개발하던
**[CaptCore/Pyssion](https://github.com/CaptCore/Pyssion)**을 이어가는 레포입니다.
이전 계정에 접근할 수 없게 되어 현재 계정 **[PrizmCaptCore](https://github.com/PrizmCaptCore)**의
**[PrizmCaptCore/Pyssion](https://github.com/PrizmCaptCore/Pyssion)**에서 개발을 이어갑니다.
기존 코드와 커밋 이력, MIT 라이선스 및 원저작자 표기를 유지합니다.

I originally developed Pyssion under my previous GitHub account, `CaptCore`.
After losing access to that account, I am continuing the project here under `PrizmCaptCore`,
preserving the existing code, commit history, original authorship, and MIT license.

---

`Pyssion().run()`

1. **Pack your code.**
2. **Ignite it on any node** — your PC, a cloud GPU VM, a RunPod pod.
3. **Bring the results home.**

The first machine you install on becomes the **manager** (the ignition point).
Every other machine joins it with a one-time token and spreads the work from there.

## Layout

| Package | Role |
|---|---|
| `pyssion.client` | SDK: pack, submit, follow logs, fetch outputs, re-attach |
| `pyssion.agent` | Node agent: joins the manager, claims jobs, runs them as a process (default) or container |
| `pyssion.reactor` | Training SDK: workers exchange weights through storage, an aggregator averages them |
| `pyssion.manager` | Management server: tokens, nodes, jobs, storage, Terraform/RunPod provisioning, control rods |
| `pyssion.bootstrap` | `pyssion init`: manager + first node + hello-world in one go |
| `pyssion.legacy` | Previous Kubernetes + MinIO implementation, kept for reference |

The SDK, agent and reactor client use only the Python standard library.

## Install & ignite

```bash
pip install -e ".[server]"
pyssion init --public-url http://<address-nodes-can-reach>:8470
```

`init` starts the manager, joins this machine as the first node, and runs a hello-world job whose
output comes back to `./pyssion_results/`. Admin credentials are saved to `~/.pyssion/client.json`.

## Spread

```bash
pyssion token --kind join                      # prints a one-time join token + the commands below
curl -fsSL http://MANAGER:8470/agent/install.sh | sh -s -- <join-token>   # any Linux box
pyssion agent --server http://MANAGER:8470 --join <join-token>           # any machine with pyssion
```

Nodes only need outbound access to the manager, so NAT and private networks are fine.

Provisioned environments (credentials come from the manager's own env vars, never the database):

```bash
pyssion env set aws-a10 --provisioner terraform --max-nodes 4 --idle 1800 --ttl 86400 \
  --config '{"module": "aws", "vars": {"region": "us-east-1", "instance_type": "g5.xlarge"}}'
pyssion env up aws-a10 --count 2
pyssion env set pod-4090 --provisioner runpod --max-nodes 8 --config '{"gpu_type": "NVIDIA GeForce RTX 4090"}'
```

Built-in Terraform modules: `aws`, `gcp`, `azure`, `nhn`. Any module that takes `name`, `server_url`,
`join_token` and outputs `id` works. `tofu` or `terraform` must be installed on the manager host.

**Control rods** keep the chain reaction bounded: `max_nodes` per env, `ttl` and `idle` destroy machines,
nodes that never join are destroyed, silent nodes go offline and their jobs are marked lost,
and `pyssion kill` cancels every job and destroys every provisioned machine.

## Run

```python
# train.py
from pyssion import Pyssion

Pyssion().run(gpus=1)   # locally: ships this project, streams logs, fetches outputs/, exits
                        # on the node: returns None and the script simply continues
...train...
```

```bash
pyssion run --gpus 1 --env aws-a10 train.py --lr 3e-4   # options before the entrypoint
pyssion run --detach train.py                           # then, from anywhere with the config:
pyssion logs <job> ; pyssion fetch <job> ; pyssion history
```

- `requirements.txt` in the project is installed into a per-job venv (uv if present) that still sees the host's torch.
- Anything the job writes under `outputs/` is uploaded while it runs and downloaded when it finishes.
- `.pyssionignore` excludes files from the upload.

## Distributed training (Reactor)

```python
from pyssion.reactor import Worker

w = Worker()                       # session, rank and world size come from the job env
for epoch in range(10):
    train_one_epoch(model)
    w.step(model, n_samples=len(dataset))   # push weights, get the sample-weighted average back
```

```bash
pyssion run --replicas 4 --gpus 1 fed.py   # rank 0 also hosts the aggregator
```

## Storage

`local` (default, the manager's disk) or any S3-compatible store (AWS S3, MinIO, GCS interop,
NHN Object Storage, R2). Set `storage`, `s3_endpoint`, `s3_access`, `s3_secret`, `s3_bucket`
in `~/.pyssion/server/server.json` or as `PYSSION_S3_*` env vars. Data always moves through presigned
URLs, never through the API.

## Requirements

- Python 3.9+
- Manager: `pip install ".[server]"` (add `.[postgres]` or `.[runpod]` as needed)
- Reactor: `torch` on the nodes

This project is licensed under the MIT License – see the [LICENSE](./LICENSE) file for details.
