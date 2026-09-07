from pathlib import Path

CREATED_BY_TAG: str = "wisp"
PULUMI_STACK_NAME: str = "wisp-stack"
PULUMI_PROJECT_NAME: str = "wisp-project"

DEFAULT_TAG = {
    "created-by": CREATED_BY_TAG,
}

DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS: int = 60

# Project root, derived from this file's location (src/wisp/config/constants.py)
ROOTDIR = Path(__file__).resolve().parents[3]

# Project paths
WIREGUARD_SCRIPT_PATH = ROOTDIR / "scripts" / "wireguard-install.sh"
WIREGUARD_PLAYBOOK_PATH = ROOTDIR / "ansible" / "wireguard_install.yaml"
WIREGUARD_INVENTORY_TEMPLATE_PATH = ROOTDIR / "templates" / "inventory.ini.j2"
WIREGUARD_INVENTORY_PATH = ROOTDIR / "inventory" / "inventory.ini"
WIREGUARD_KEYS_DIR = ROOTDIR / "keys"
WIREGUARD_KEY_PATH = WIREGUARD_KEYS_DIR / "wireguard-key.pem"
WIREGUARD_CLIENT_CONF_PATH = ROOTDIR / "wireguard-confs" / "wg0-client.conf"

# WireGuard defaults (non-interactive installer)
WIREGUARD_INTERFACE: str = "wg0"
WIREGUARD_IPV4: str = "10.66.66.1"
WIREGUARD_IPV6: str = "fd42:42:42::1"
WIREGUARD_DNS1: str = "1.1.1.1"
WIREGUARD_DNS2: str = "1.0.0.1"
WIREGUARD_CLIENT_NAME: str = ""
