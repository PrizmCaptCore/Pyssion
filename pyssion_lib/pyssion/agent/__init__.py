"""Node agent: joins the manager, claims jobs, runs them, reports back."""
from .node import Agent, detect_gpus
from .task import Task

__all__ = ["Agent", "Task", "detect_gpus"]
