"""Typed data structures shared across the application."""

from pathlib import Path
from typing import TypedDict


class InventoryContext(TypedDict):
    """Variables consumed by the Ansible inventory template
    (``templates/inventory.ini.j2``).

    Populated during deploy from the Pulumi stack outputs and the active
    :class:`~wisp.config.settings.WispConfig`, then rendered into
    ``inventory/inventory.ini``.
    """

    ssh_user: str
    instance_ip: str
    ssh_key_file: str | Path
    wireguard_port: int | str
    allowed_ips: str
    wireguard_public_ip: str
    wireguard_interface: str
    wireguard_ipv4: str
    wireguard_ipv6: str
    wireguard_dns1: str
    wireguard_dns2: str
    wireguard_client_name: str
    wireguard_client_ipv4: str
    wireguard_client_ipv6: str
    wireguard_skip_client: str
