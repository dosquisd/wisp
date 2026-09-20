"""Project-wide constants: tags, Pulumi identity, filesystem paths, and
WireGuard defaults.

All paths are derived from :data:`ROOTDIR`, which is resolved from this file's
location (``src/wisp/config/constants.py`` → three parents up = repo root).
"""

import os
import platform
from pathlib import Path


def __project_root(anchor: str = "pyproject.toml"):
    path = Path.cwd()
    for parent in [path] + list(path.parents):
        if (parent / anchor).exists():
            return parent
    raise FileNotFoundError(
        f"Could not find {anchor} in the parent directories of {path}"
    )


CREATED_BY_TAG: str = "wisp"
PULUMI_PROJECT_NAME: str = "wisp-project"


def get_pulumi_stack_name(provider: str) -> str:
    """Get provider-specific Pulumi stack name."""
    return f"wisp-stack-{provider}"


DEFAULT_TAG = {
    "created-by": CREATED_BY_TAG,
}

DEFAULT_VM_BOOT_TIMEOUT_SECONDS: int = 60

# Project root, derived from this file's location (src/wisp/config/constants.py)
try:
    ROOTDIR = __project_root()
except FileNotFoundError:
    ROOTDIR = Path(__file__).resolve().parents[3]

# Project paths
WIREGUARD_SCRIPT_PATH = ROOTDIR / "scripts" / "wireguard-server-install.sh"
WIREGUARD_KEYS_DIR = ROOTDIR / "keys"
WIREGUARD_KEY_PATH = WIREGUARD_KEYS_DIR / "wireguard-key.pem"
WIREGUARD_CLIENT_CONF_PATH = ROOTDIR / "wireguard-confs" / "wg0-client.conf"


def _get_user_config_dir() -> Path:
    """Get the user-level config directory for Wisp."""
    system = platform.system().lower()
    if system == "windows":
        return (
            Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            / "wisp"
        )
    elif system == "darwin":
        return Path.home() / "Library" / "Application Support" / "wisp"

    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "wisp"


def __prepare_config_file(path: Path) -> None:
    """Ensure the config file exists and is secure (owner-only)."""
    from wisp.utils.platform import secure_file

    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    secure_file(path)


WISP_CONFIG_FILE_NAME: str = "wisp.toml"
WISP_PROJECT_CONFIG_PATH = ROOTDIR / WISP_CONFIG_FILE_NAME
WISP_USER_CONFIG_PATH = _get_user_config_dir() / WISP_CONFIG_FILE_NAME

__prepare_config_file(WISP_USER_CONFIG_PATH)
__prepare_config_file(WISP_PROJECT_CONFIG_PATH)

# WireGuard defaults (non-interactive installer)
WIREGUARD_INTERFACE: str = "wg0"
WIREGUARD_IPV4: str = "10.66.66.1"
WIREGUARD_IPV6: str = "fd42:42:42::1"
WIREGUARD_DNS1: str = "1.1.1.1"
WIREGUARD_DNS2: str = "1.0.0.1"
WIREGUARD_CLIENT_NAME: str = ""

# Provider default regions
AWS_DEFAULT_REGION: str = "us-east-2"
OCI_DEFAULT_COMPARTMENT_ID: str = ""
