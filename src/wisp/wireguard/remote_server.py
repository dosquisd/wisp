import subprocess

from wisp.config.constants import (
    WIREGUARD_INVENTORY_PATH,
    WIREGUARD_INVENTORY_TEMPLATE_PATH,
    WIREGUARD_PLAYBOOK_PATH,
)
from wisp.schemas import InventoryContext
from wisp.utils import get_ansible_playbook_bin, render_inventory_template
from wisp.utils import (
    logger,
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
        WIREGUARD_INVENTORY_PATH, # type: ignore
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
