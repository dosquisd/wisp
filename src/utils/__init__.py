from urllib.request import urlopen

from src.utils.ansible import get_ansible_playbook_bin
from src.utils.logger import logger
from src.utils.pulumi import create_or_select_pulumi_stack
from src.utils.randoms import get_random_generator, get_wireguard_port
from src.utils.templates import render_inventory_template

__all__ = [
    "create_or_select_pulumi_stack",
    "get_ansible_playbook_bin",
    "get_public_ip",
    "get_random_generator",
    "get_wireguard_port",
    "logger",
    "render_inventory_template",
]


def get_public_ip() -> str:
    with urlopen("https://api.ipify.org") as response:
        return response.read().decode("utf-8")
