# This is far to be completed. There is some crucial details missing:
# 1. Architecture design. Currently, the code only supports one Virtual Machine (VM) per stack,
# the idea is to support multiple VMs per stack. This requires a more complex architecture design and an more
# appropiate state management, the current implementation is not scalable and does not work with multiple VMs.
# 2. For the same reason, the delete_vm must be refactored to support deleting a specific VM from the stack,
# instead of destroying the entire stack.
# 3. Same as delete_vm, there should be a method to stop a specific VM, instead of stopping the entire stack.

import os
import subprocess
import time
from collections.abc import Sequence

import boto3
from tqdm import tqdm

from src.config.constants import (
    DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS,
    WIREGUARD_DNS1,
    WIREGUARD_DNS2,
    WIREGUARD_INTERFACE,
    WIREGUARD_INVENTORY_PATH,
    WIREGUARD_INVENTORY_TEMPLATE_PATH,
    WIREGUARD_IPV4,
    WIREGUARD_IPV6,
    WIREGUARD_KEY_PATH,
    WIREGUARD_KEYS_DIR,
    WIREGUARD_PLAYBOOK_PATH,
)
from src.providers.aws.constants import DEFAULT_REGION
from src.providers.aws.pulumi import create_ec2_instance
from src.providers.base import BaseProvider, DeployVMResult
from src.utils import (
    create_or_select_pulumi_stack,
    get_ansible_playbook_bin,
    get_public_ip,
    logger,
    render_inventory_template,
)


class AWSProvider(BaseProvider):
    def __create_pulumi_program(self, region: str) -> None:
        create_ec2_instance(region)

    def get_available_regions(self) -> Sequence[str]:
        client = boto3.client("ec2", region_name=DEFAULT_REGION)
        return [r["RegionName"] for r in client.describe_regions()["Regions"]]

    def deploy_vm(self, region: str, force_current_ip: bool = False) -> DeployVMResult:
        stack = create_or_select_pulumi_stack(
            lambda: self.__create_pulumi_program(region)
        )
        up_result = stack.up()

        # Wait for the stack to be fully deployed before retrieving outputs
        logger.debug(
            f"Waiting for {DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS} "
            "seconds for the stack to be fully deployed..."
        )
        for _ in tqdm(
            range(DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS),
            desc="Waiting for stack to deploy",
        ):
            time.sleep(1)

        outputs = up_result.outputs
        instance_id = outputs["instance_id"].value
        public_ip = outputs["instance_public_ip"].value
        private_ip = outputs["instance_private_ip"].value
        private_key = outputs["instance_private_key"].value
        wireguard_port = outputs["wireguard_port"].value
        ssh_user = outputs["ssh_user"].value
        logger.debug(
            f"Deployed VM '{instance_id}' at '{public_ip}' with SSH user '{ssh_user}'"
        )

        # Write the WireGuard/SSH private key
        WIREGUARD_KEYS_DIR.mkdir(parents=True, exist_ok=True)
        with open(
            WIREGUARD_KEY_PATH,
            "w",
            opener=lambda p, f: os.open(p, f, 0o600),
        ) as f:
            f.write(private_key)
        logger.debug(
            f"Private key written to '{WIREGUARD_KEY_PATH}' with permissions 600"
        )

        # Determine the allowed IPs for the WireGuard clients
        allowed_ips = f"{get_public_ip()}/32" if force_current_ip else "0.0.0.0/0,::/0"

        # Render the Ansible inventory from the template
        template_context = {
            "ssh_user": ssh_user,
            "instance_ip": public_ip,
            "ssh_key_file": WIREGUARD_KEY_PATH,
            "wireguard_port": wireguard_port,
            "allowed_ips": allowed_ips,
            "wireguard_public_ip": public_ip,
            "wireguard_interface": WIREGUARD_INTERFACE,
            "wireguard_ipv4": WIREGUARD_IPV4,
            "wireguard_ipv6": WIREGUARD_IPV6,
            "wireguard_dns1": WIREGUARD_DNS1,
            "wireguard_dns2": WIREGUARD_DNS2,
            "wireguard_client_name": "",
            "wireguard_client_ipv4": "",
            "wireguard_client_ipv6": "",
            "wireguard_skip_client": "n",
        }
        render_inventory_template(
            template_path=WIREGUARD_INVENTORY_TEMPLATE_PATH,
            output_path=WIREGUARD_INVENTORY_PATH,
            context=template_context,
            mode=0o644,
        )

        logger.debug(f"Ansible inventory written to '{WIREGUARD_INVENTORY_PATH}'")

        # Run the Ansible playbook to install WireGuard
        ansible_playbook_bin = get_ansible_playbook_bin()
        logger.debug(f"Running Ansible playbook using '{ansible_playbook_bin}'")
        subprocess.run(
            [
                ansible_playbook_bin,
                "-i",
                str(WIREGUARD_INVENTORY_PATH),
                str(WIREGUARD_PLAYBOOK_PATH),
            ],
            check=True,
        )

        return DeployVMResult(
            instance_id=instance_id,
            public_ip=public_ip,
            private_ip=private_ip,
        )

    def delete_vm(self, region: str) -> int:
        stack = create_or_select_pulumi_stack(
            lambda: self.__create_pulumi_program(region)
        )

        try:
            destroy_result = stack.destroy()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error destroying stack: {e}")
            return 0

        # Remove the WireGuard inventory and key files if they exist
        if WIREGUARD_INVENTORY_PATH.exists():
            os.remove(WIREGUARD_INVENTORY_PATH)

        if WIREGUARD_KEY_PATH.exists():
            os.remove(WIREGUARD_KEY_PATH)

        return destroy_result.summary.resource_changes.get("delete", 0)  # type: ignore
