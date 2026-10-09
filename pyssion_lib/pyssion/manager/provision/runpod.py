"""GPU clouds without a solid Terraform provider are driven by their API. Pods are already containers,
so the agent runs in the foreground with the process executor.

env.config = {"gpu_type": "NVIDIA GeForce RTX 4090", "gpus": 1, "image": "...", "cloud": "ALL", "disk_gb": 50}
"""
import os


class RunPod:
    IMAGE = "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"

    def __init__(self, env):
        import runpod
        runpod.api_key = os.environ["RUNPOD_API_KEY"]
        self.rp, self.cfg = runpod, env.config or {}

    def up(self, name, server_url, join_token):
        boot = f'bash -c "curl -fsSL {server_url}/agent/install.sh | sh -s -- {join_token} --foreground"'
        pod = self.rp.create_pod(
            name=name, image_name=self.cfg.get("image", self.IMAGE),
            gpu_type_id=self.cfg.get("gpu_type", "NVIDIA GeForce RTX 4090"), gpu_count=self.cfg.get("gpus", 1),
            cloud_type=self.cfg.get("cloud", "ALL"), container_disk_in_gb=self.cfg.get("disk_gb", 50),
            docker_args=boot,
            env={"PYSSION_NODE_NAME": name, "PYSSION_ORPHAN_CMD": "runpodctl remove pod $RUNPOD_POD_ID"})
        return pod["id"]

    def down(self, ref):
        self.rp.terminate_pod(ref)
