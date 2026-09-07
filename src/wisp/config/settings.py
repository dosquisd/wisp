"""Per-session configuration model (:class:`WispConfig`)."""

from dataclasses import dataclass

from wisp.config.constants import (
    DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS,
    WIREGUARD_DNS1,
    WIREGUARD_DNS2,
    WIREGUARD_INTERFACE,
    WIREGUARD_IPV4,
    WIREGUARD_IPV6,
)


@dataclass
class WispConfig:
    """Per-session deployment settings.

    Edited in memory by the TUI Configuration screen (not persisted to disk).
    Defaults are drawn from :mod:`wisp.config.constants`.

    Attributes:
        ansible_timeout (int): Seconds to wait for the VM to boot / SSH to come
            up before running Ansible.
        wireguard_interface (str): WireGuard interface name (e.g. ``wg0``).
        wireguard_ipv4 (str): Server-side WireGuard IPv4 address.
        wireguard_ipv6 (str): Server-side WireGuard IPv6 address.
        wireguard_dns1 (str): Primary DNS pushed to the client.
        wireguard_dns2 (str): Secondary DNS pushed to the client.
        wireguard_port (int): UDP port; ``0`` selects a random port in
            ``49152-65535``.
        force_current_ip (bool): If true, restrict the firewall and client
            AllowedIPs to your current public IP (``/32``).
    """

    ansible_timeout: int = DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS
    wireguard_interface: str = WIREGUARD_INTERFACE
    wireguard_ipv4: str = WIREGUARD_IPV4
    wireguard_ipv6: str = WIREGUARD_IPV6
    wireguard_dns1: str = WIREGUARD_DNS1
    wireguard_dns2: str = WIREGUARD_DNS2
    wireguard_port: int = 0  # 0 indicates dynamic random port (49152-65535)
    force_current_ip: bool = False
