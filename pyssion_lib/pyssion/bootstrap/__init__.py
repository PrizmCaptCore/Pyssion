"""First ignition: turn this machine into the manager, join it as the first node, run hello-world."""
from .hello import hello
from .ignite import init, stop

__all__ = ["init", "stop", "hello"]
