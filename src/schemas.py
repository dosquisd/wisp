from pathlib import Path
from typing import TypedDict


class InventoryContext(TypedDict):
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
