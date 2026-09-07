"""Shared utility helpers.

Common helpers are re-exported here; the heavier Pulumi/Jinja helpers
(``create_or_select_pulumi_stack``, ``render_inventory_template``) are imported
lazily via module ``__getattr__`` to avoid importing Pulumi at package load.
"""

from urllib.request import urlopen

from wisp.utils.ansible import get_ansible_playbook_bin
from wisp.utils.logger import logger
from wisp.utils.randoms import get_random_generator, get_wireguard_port


def __getattr__(name: str):
    """Lazily import the Pulumi/Jinja helpers on first attribute access."""
    if name == "create_or_select_pulumi_stack":
        from wisp.utils.pulumi import create_or_select_pulumi_stack

        return create_or_select_pulumi_stack

    if name == "render_inventory_template":
        from wisp.utils.templates import render_inventory_template

        return render_inventory_template

    raise AttributeError(f"module {__name__} has no attribute {name}")


def get_public_ip() -> str:
    """Return the machine's current public IPv4 address (via api.ipify.org)."""
    with urlopen("https://api.ipify.org") as response:
        return response.read().decode("utf-8")


__all__ = [
    "get_ansible_playbook_bin",
    "get_public_ip",
    "get_random_generator",
    "get_wireguard_port",
    "logger",
]
