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

    Search order (later files override earlier ones, key by key):
    1. Project-level: ``<repo root>/wisp.toml``.
    2. User-level: ``~/.config/wisp/wisp.toml`` (Linux),
       ``~/Library/Application Support/wisp/wisp.toml`` (macOS),
       ``%APPDATA%\\wisp\\wisp.toml`` (Windows) — **wins** on any key set
       in both, since it's the file meant to follow you across projects.
       See :func:`get_active_config_path` for the single-file equivalent
       of this rule (used as the write target when the TUI saves).

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
    """Read and merge project-level + user-level TOML files (no caching).

    Iterated in this order (project first, user second) so that, per
    section, ``dict.update`` lets the user-level value win on shared keys —
    see :func:`get_active_config_path` for why user-level takes priority.
    """
    config: dict[str, Any] = {}

    for path in (WISP_PROJECT_CONFIG_PATH, WISP_USER_CONFIG_PATH):
        parsed = _read_toml_file(path)
        if not parsed:
            continue
        # Merge section by section so user-level keys override project-level.
        for section, values in parsed.items():
            if section not in config:
                config[section] = {}
            if isinstance(values, dict):
                config[section].update(values)

    return config


def get_active_config_path() -> Path:
    """Return the single wisp.toml that reads/writes should treat as primary.

    :func:`load_toml_config` already merges *both* files for reading, with
    the user-level file winning key by key. But a single canonical file is
    still needed as the *write* target — e.g. for the TUI's "Guardar" action
    — so this is the one place that decides which file that is, instead of
    every caller re-deriving it with its own little existence check (which
    is exactly the kind of scattered logic this function replaces).

    Preference order:
    1. The user-level file, if it has any parsed content.
    2. The project-level file, if *that* has content (and the user-level
       one doesn't).
    3. The user-level path, as the default target for a first-ever save —
       both files always exist on disk (see
       :func:`wisp.config.constants.__prepare_config_file`), just possibly
       empty, so "has content" is the only meaningful distinguishing check.
    """
    if _read_toml_file(WISP_USER_CONFIG_PATH):
        return WISP_USER_CONFIG_PATH
    if _read_toml_file(WISP_PROJECT_CONFIG_PATH):
        return WISP_PROJECT_CONFIG_PATH
    return WISP_USER_CONFIG_PATH


def describe_config_sources() -> str:
    """Rich-markup one-liner on which wisp.toml is active, for TUI/log display.

    Flags the ambiguous case explicitly (both files have data) instead of
    silently picking one, since that's exactly the situation that made this
    worth a dedicated notice in the first place.
    """
    user_has_data = bool(_read_toml_file(WISP_USER_CONFIG_PATH))
    project_has_data = bool(_read_toml_file(WISP_PROJECT_CONFIG_PATH))
    active = get_active_config_path()

    if user_has_data and project_has_data:
        return (
            f"[yellow]⚠[/yellow] Hay dos wisp.toml con datos (usuario y proyecto). "
            f"Usando el de [bold]usuario[/bold]: [cyan]{active}[/cyan] — el de "
            f"proyecto solo rellena claves que ese no defina."
        )
    return f"[dim]Config activa:[/dim] [cyan]{active}[/cyan]"


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


# ─── Writing back to disk ─────────────────────────────────────────


def _write_toml_raw(path: Path, data: dict[str, Any]) -> None:
    """Write ``data`` as TOML to a single file, creating/securing it.

    Requires the ``tomli-w`` package (``tomllib`` is read-only, by design —
    it has no writer). Add it to the project's dependencies if it isn't
    there yet: ``uv add tomli-w``.
    """
    import tomli_w

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        tomli_w.dump(data, f)

    from wisp.utils.platform import secure_file  # deferred: avoid import cycle

    secure_file(path)


def save_session_config(
    cfg: "WispConfig",
    provider_regions: dict[str, str] | None = None,
    path: Path | None = None,
) -> Path:
    """Persist ``cfg`` (and optionally per-provider regions) to one wisp.toml.

    Only two things in the target file are touched:
    - The ``[general]`` section is *updated* (not replaced) with ``cfg``'s
      fields, so unrelated keys already there — e.g. ``default_provider``,
      which lives in ``[general]`` but isn't part of :class:`WispConfig` —
      survive the save.
    - For each ``provider: region`` pair in ``provider_regions``, only that
      section's ``region`` key is set (or removed, if ``region`` is empty).
      Everything else in that section (credentials, profile, etc.) is left
      exactly as-is — this function never writes secrets.

    The *other* wisp.toml (project vs. user) is never touched. Defaults to
    :func:`get_active_config_path` when ``path`` isn't given.

    Returns:
        Path: The file that was actually written, so the caller can tell
            the user where their settings went.
    """
    target = path or get_active_config_path()
    data = _read_toml_file(target)

    general_section = data.setdefault("general", {})
    general_section.update(
        {
            "vm_boot_timeout": cfg.vm_boot_timeout,
            "wireguard_interface": cfg.wireguard_interface,
            "wireguard_ipv4": cfg.wireguard_ipv4,
            "wireguard_ipv6": cfg.wireguard_ipv6,
            "wireguard_dns1": cfg.wireguard_dns1,
            "wireguard_dns2": cfg.wireguard_dns2,
            "wireguard_port": cfg.wireguard_port,
            "force_current_ip": cfg.force_current_ip,
        }
    )

    for provider, region in (provider_regions or {}).items():
        section = data.setdefault(provider, {})
        if region:
            section["region"] = region
        else:
            section.pop("region", None)

    _write_toml_raw(target, data)
    reload_toml_config()
    return target


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
