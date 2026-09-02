from dataclasses import dataclass

from src.config.constants import (
    DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS,
    WIREGUARD_DNS1,
    WIREGUARD_DNS2,
    WIREGUARD_INTERFACE,
    WIREGUARD_IPV4,
    WIREGUARD_IPV6,
)


@dataclass
class WispConfig:
    ansible_timeout: int = DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS
    wireguard_interface: str = WIREGUARD_INTERFACE
    wireguard_ipv4: str = WIREGUARD_IPV4
    wireguard_ipv6: str = WIREGUARD_IPV6
    wireguard_dns1: str = WIREGUARD_DNS1
    wireguard_dns2: str = WIREGUARD_DNS2
    wireguard_port: int = 0  # 0 indicates dynamic random port (49152-65535)
    force_current_ip: bool = False
