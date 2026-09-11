"""Shared utility helpers.

Common helpers are re-exported here; the heavier Pulumi helpers
(``create_or_select_pulumi_stack``) are imported lazily via module ``__getattr__``
to avoid importing Pulumi at package load.
"""

from urllib.request import urlopen

from wisp.utils.logger import logger
from wisp.utils.platform import PlatformEnum
from wisp.utils.randoms import get_random_generator, get_wireguard_port


def __getattr__(name: str):
    """Lazily import the Pulumi helpers on first attribute access."""
    if name == "create_or_select_pulumi_stack":
        from wisp.utils.pulumi import create_or_select_pulumi_stack

        return create_or_select_pulumi_stack

    raise AttributeError(f"module {__name__} has no attribute {name}")


def get_public_ip() -> str:
    """Return the machine's current public IPv4 address (via api.ipify.org)."""
    with urlopen("https://api.ipify.org") as response:
        return response.read().decode("utf-8")


__all__ = [
    "get_public_ip",
    "get_random_generator",
    "get_wireguard_port",
    "logger",
    "PlatformEnum",
]
