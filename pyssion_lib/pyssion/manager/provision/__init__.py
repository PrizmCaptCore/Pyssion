"""Turns an env into machines that boot the agent and join with a one-time token.

Every provisioner has the same two calls:
    up(name, server_url, join_token) -> ref
    down(ref)
Cloud credentials come from the manager's own environment (AWS_*, GOOGLE_*, ARM_*, OS_*, RUNPOD_API_KEY),
never from the database.
"""


def provisioner(env):
    if env.provisioner == "terraform":
        from .terraform import Terraform
        return Terraform(env)
    if env.provisioner == "runpod":
        from .runpod import RunPod
        return RunPod(env)
    raise ValueError(f"env '{env.name}' uses provisioner '{env.provisioner}', which cannot create nodes")


__all__ = ["provisioner"]
