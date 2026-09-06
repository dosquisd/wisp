from urllib.request import urlopen

from src.utils.ansible import get_ansible_playbook_bin
from src.utils.logger import logger
from src.utils.randoms import get_random_generator, get_wireguard_port


def __getattr__(name: str):
    if name == "create_or_select_pulumi_stack":
        from src.utils.pulumi import create_or_select_pulumi_stack

        return create_or_select_pulumi_stack

    if name == "render_inventory_template":
        from src.utils.templates import render_inventory_template

        return render_inventory_template


def get_public_ip() -> str:
    with urlopen("https://api.ipify.org") as response:
        return response.read().decode("utf-8")


__all__ = [
    "get_ansible_playbook_bin",
    "get_public_ip",
    "get_random_generator",
    "get_wireguard_port",
    "logger",
]
