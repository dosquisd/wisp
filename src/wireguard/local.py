# Local configuration of WireGuard client

import shutil
import subprocess
from pathlib import Path

from src.utils import logger


def configure_local_wireguard_client(wireguard_client_conf_path: str | Path) -> None:
    dest_path = Path("/etc/wireguard/wg0.conf")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(wireguard_client_conf_path, dest_path)

    dest_path.chmod(0o600)

    connect_wireguard_client()


def connect_wireguard_client() -> None:
    commands = ["sudo", "wg-quick", "up", "wg0"]

    logger.debug(f"Running command: {' '.join(commands)}")

    subprocess.run(commands, check=True, text=True)


def disconnect_wireguard_client() -> None:
    commands = ["sudo", "wg-quick", "down", "wg0"]

    logger.debug(f"Running command: {' '.join(commands)}")

    subprocess.run(commands, check=True, text=True)
