import subprocess

from src.config.constants import (
    WIREGUARD_INVENTORY_PATH,
    WIREGUARD_INVENTORY_TEMPLATE_PATH,
    WIREGUARD_PLAYBOOK_PATH,
)
from src.schemas import InventoryContext
from src.utils import (
    get_ansible_playbook_bin,
    logger,
    render_inventory_template,
)


def configure_remote_server(inventory_context: InventoryContext) -> None:
    """
    Configure the remote WireGuard server using Ansible.

    Args:
        inventory_context (InventoryContext): Context containing variables for the Ansible inventory.
    """
    # Render the Ansible inventory from the template
    render_inventory_template(
        WIREGUARD_INVENTORY_TEMPLATE_PATH,
        WIREGUARD_INVENTORY_PATH,
        inventory_context,
    )

    # Run the Ansible playbook to configure the WireGuard server
    ansible_playbook_bin = get_ansible_playbook_bin()
    command = [
        ansible_playbook_bin,
        "-i",
        str(WIREGUARD_INVENTORY_PATH),
        str(WIREGUARD_PLAYBOOK_PATH),
    ]
    logger.debug(f"Running Ansible playbook: {' '.join(command)}")
    subprocess.run(command, check=True)
