from urllib.request import urlopen

from wisp.utils.ansible import get_ansible_playbook_bin
from wisp.utils.logger import logger
from wisp.utils.randoms import get_random_generator, get_wireguard_port


def __getattr__(name: str):
    if name == "create_or_select_pulumi_stack":
        from wisp.utils.pulumi import create_or_select_pulumi_stack

        return create_or_select_pulumi_stack

    if name == "render_inventory_template":
        from wisp.utils.templates import render_inventory_template

        return render_inventory_template

    raise AttributeError(f"module {__name__} has no attribute {name}")


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
