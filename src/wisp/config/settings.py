"""Per-session and persistent configuration model (:class:`WispConfig`)."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_path

from wisp.config.constants import (
    DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS,
    WIREGUARD_DNS1,
    WIREGUARD_DNS2,
    WIREGUARD_INTERFACE,
    WIREGUARD_IPV4,
    WIREGUARD_IPV6,
)
from wisp.utils.logger import logger


def get_config_file_path() -> Path:
    """Return the platform-specific path to the Wisp configuration file."""
    config_dir = user_config_path("wisp", appauthor=False)
    return config_dir / "config.toml"


@dataclass
class WispConfig:
    """Wisp deployment settings with TOML persistence.

    Attributes:
        ansible_timeout (int): Seconds to wait for VM boot and SSH initialization.
        wireguard_interface (str): WireGuard interface name (default ``wg0``).
        wireguard_ipv4 (str): Server tunnel IPv4 address.
        wireguard_ipv6 (str): Server tunnel IPv6 address.
        wireguard_dns1 (str): Primary DNS server pushed to the client.
        wireguard_dns2 (str): Secondary DNS server pushed to the client.
        wireguard_port (int): UDP port; ``0`` selects a dynamic random port.
        force_current_ip (bool): Restrict access to the caller's public IP (/32).
    """

    ansible_timeout: int = DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS
    wireguard_interface: str = WIREGUARD_INTERFACE
    wireguard_ipv4: str = WIREGUARD_IPV4
    wireguard_ipv6: str = WIREGUARD_IPV6
    wireguard_dns1: str = WIREGUARD_DNS1
    wireguard_dns2: str = WIREGUARD_DNS2
    wireguard_port: int = 0  # 0 indicates dynamic random port (49152-65535)
    force_current_ip: bool = False

    def to_toml(self) -> str:
        """Serialize configuration to a formatted TOML string."""
        return (
            "# Wisp Configuration File\n"
            "# Automatically managed by Wisp CLI / TUI.\n\n"
            "[ansible]\n"
            "# Seconds to wait for the VM to boot before running Ansible\n"
            f"timeout = {self.ansible_timeout}\n\n"
            "[wireguard]\n"
            f'interface = "{self.wireguard_interface}"\n'
            f'ipv4 = "{self.wireguard_ipv4}"\n'
            f'ipv6 = "{self.wireguard_ipv6}"\n'
            f'dns1 = "{self.wireguard_dns1}"\n'
            f'dns2 = "{self.wireguard_dns2}"\n'
            "# 0 means dynamic random port (49152-65535)\n"
            f"port = {self.wireguard_port}\n\n"
            "[security]\n"
            "# Restrict firewall ingress to your current public IP (/32)\n"
            f"force_current_ip = {'true' if self.force_current_ip else 'false'}\n"
        )

    @classmethod
    def from_toml(cls, toml_str: str) -> "WispConfig":
        """Deserialize a configuration instance from a TOML string."""
        data = tomllib.loads(toml_str)
        ansible = data.get("ansible", {})
        wireguard = data.get("wireguard", {})
        security = data.get("security", {})
        return cls(
            ansible_timeout=int(
                ansible.get("timeout", DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS)
            ),
            wireguard_interface=str(wireguard.get("interface", WIREGUARD_INTERFACE)),
            wireguard_ipv4=str(wireguard.get("ipv4", WIREGUARD_IPV4)),
            wireguard_ipv6=str(wireguard.get("ipv6", WIREGUARD_IPV6)),
            wireguard_dns1=str(wireguard.get("dns1", WIREGUARD_DNS1)),
            wireguard_dns2=str(wireguard.get("dns2", WIREGUARD_DNS2)),
            wireguard_port=int(wireguard.get("port", 0)),
            force_current_ip=bool(security.get("force_current_ip", False)),
        )

    @classmethod
    def load(cls, path: Path | None = None) -> "WispConfig":
        """Load configuration from TOML file, falling back to defaults if not found."""
        target_path = path or get_config_file_path()
        if not target_path.is_file():
            return cls()

        try:
            with open(target_path, "rb") as f:
                data = tomllib.load(f)
            ansible = data.get("ansible", {})
            wireguard = data.get("wireguard", {})
            security = data.get("security", {})
            return cls(
                ansible_timeout=int(
                    ansible.get("timeout", DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS)
                ),
                wireguard_interface=str(
                    wireguard.get("interface", WIREGUARD_INTERFACE)
                ),
                wireguard_ipv4=str(wireguard.get("ipv4", WIREGUARD_IPV4)),
                wireguard_ipv6=str(wireguard.get("ipv6", WIREGUARD_IPV6)),
                wireguard_dns1=str(wireguard.get("dns1", WIREGUARD_DNS1)),
                wireguard_dns2=str(wireguard.get("dns2", WIREGUARD_DNS2)),
                wireguard_port=int(wireguard.get("port", 0)),
                force_current_ip=bool(security.get("force_current_ip", False)),
            )
        except Exception as exc:
            logger.warning(
                f"Could not load config from {target_path}: {exc}. Using defaults."
            )
            return cls()

    def save(self, path: Path | None = None) -> Path:
        """Persist configuration to the target TOML file."""
        target_path = path or get_config_file_path()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(self.to_toml(), encoding="utf-8")
        logger.debug(f"Configuration saved to {target_path}")
        return target_path
