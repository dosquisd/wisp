"""Global and per-session configuration.

The global configuration is loaded from ``wisp.toml`` (user-level and
project-level merged) — this is the first thing Wisp loads at startup. It
holds provider credentials, per-provider defaults, and general defaults
(:data:`get_default_provider`, :data:`get_default_region_for`).

:class:`WispConfig` is the per-session deployment settings object, built from
the ``[general]`` TOML section via :func:`load_wisp_config` and edited in
memory by the TUI Configuration screen (never persisted back to disk).

Provider-specific values (``[aws]``, ``[oci]``) are resolved by
:mod:`wisp.config.credentials`, including each provider's own default region.
There is deliberately no cross-provider default region.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wisp.config.constants import (
    DEFAULT_VM_BOOT_TIMEOUT_SECONDS,
    WIREGUARD_DNS1,
    WIREGUARD_DNS2,
    WIREGUARD_INTERFACE,
    WIREGUARD_IPV4,
    WIREGUARD_IPV6,
    WISP_PROJECT_CONFIG_PATH,
    WISP_USER_CONFIG_PATH,
)

# ─── Global configuration (wisp.toml) ────────────────────────────

_cached_config: dict[str, Any] | None = None


def _read_toml_file(path: Path) -> dict[str, Any]:
    """Read and parse a TOML file, returning an empty dict on failure.

    Args:
        path (Path): Path to the TOML file.

    Returns:
        dict[str, Any]: Parsed TOML contents, or empty dict if the file
            does not exist, is unreadable, or is invalid.
    """
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except OSError, tomllib.TOMLDecodeError:
        return {}


def load_toml_config() -> dict[str, Any]:
    """Load the global TOML configuration (cached after first load).

    Search order (later files override earlier ones):
    1. User-level: ``~/.config/wisp/wisp.toml`` (Linux),
       ``~/Library/Application Support/wisp/wisp.toml`` (macOS),
       ``%APPDATA%\\wisp\\wisp.toml`` (Windows).
    2. Project-level: ``<repo root>/wisp.toml``.

    The parsed result is cached; subsequent calls return the same merged
    dict without re-reading the files. Use :func:`reload_toml_config` to
    force a fresh read (e.g. after editing values).

    Returns:
        dict[str, Any]: Merged config as a dict, or empty dict if no
            config file was found.
    """
    global _cached_config
    if _cached_config is None:
        _cached_config = _merge_toml_files()
    return _cached_config


def reload_toml_config() -> dict[str, Any]:
    """Force a fresh read of the global TOML configuration.

    Clears the cache and re-reads both config files, returning the new
    merged result.

    Returns:
        dict[str, Any]: Freshly merged config as a dict.
    """
    global _cached_config
    _cached_config = _merge_toml_files()
    return _cached_config


def _merge_toml_files() -> dict[str, Any]:
    """Read and merge user-level + project-level TOML files (no caching)."""
    config: dict[str, Any] = {}

    for path in (WISP_USER_CONFIG_PATH, WISP_PROJECT_CONFIG_PATH):
        parsed = _read_toml_file(path)
        if not parsed:
            continue
        # Merge section by section so project-level keys override user-level.
        for section, values in parsed.items():
            if section not in config:
                config[section] = {}
            if isinstance(values, dict):
                config[section].update(values)

    return config


def get_default_provider() -> str:
    """Return the default provider from ``[general]`` (fallback: ``"aws"``)."""
    return load_toml_config().get("general", {}).get("default_provider", "aws")


def get_default_region_for(provider: str) -> str:
    """Return the default region configured for a provider section.

    Regions are provider-specific (e.g. ``[aws].region``, ``[oci].region``);
    there is no cross-provider default region.

    Args:
        provider (str): Provider section name (``"aws"`` or ``"oci"``).

    Returns:
        str: The configured region, or ``""`` if not set.
    """
    return str(load_toml_config().get(provider, {}).get("region", ""))


# ─── Per-session configuration ───────────────────────────────────


def load_wisp_config() -> WispConfig:
    """Build a :class:`WispConfig` from the ``[general]`` TOML section.

    Any field omitted in the TOML falls back to the constant defaults from
    :mod:`wisp.config.constants`.

    Returns:
        WispConfig: Per-session settings populated from ``wisp.toml``.
    """
    general = load_toml_config().get("general", {})
    return WispConfig(
        vm_boot_timeout=general.get("vm_boot_timeout", DEFAULT_VM_BOOT_TIMEOUT_SECONDS),
        wireguard_interface=general.get("wireguard_interface", WIREGUARD_INTERFACE),
        wireguard_ipv4=general.get("wireguard_ipv4", WIREGUARD_IPV4),
        wireguard_ipv6=general.get("wireguard_ipv6", WIREGUARD_IPV6),
        wireguard_dns1=general.get("wireguard_dns1", WIREGUARD_DNS1),
        wireguard_dns2=general.get("wireguard_dns2", WIREGUARD_DNS2),
        wireguard_port=int(general.get("wireguard_port", 0)),
        force_current_ip=bool(general.get("force_current_ip", False)),
    )


@dataclass
class WispConfig:
    """Per-session deployment settings.

    Edited in memory by the TUI Configuration screen (not persisted to disk).
    Defaults are drawn from :mod:`wisp.config.constants`.

    Attributes:
        vm_boot_timeout (int): Seconds to wait for the VM to boot / SSH to come
            up before configuring WireGuard.
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

    vm_boot_timeout: int = DEFAULT_VM_BOOT_TIMEOUT_SECONDS
    wireguard_interface: str = WIREGUARD_INTERFACE
    wireguard_ipv4: str = WIREGUARD_IPV4
    wireguard_ipv6: str = WIREGUARD_IPV6
    wireguard_dns1: str = WIREGUARD_DNS1
    wireguard_dns2: str = WIREGUARD_DNS2
    wireguard_port: int = 0  # 0 indicates dynamic random port (49152-65535)
    force_current_ip: bool = False
