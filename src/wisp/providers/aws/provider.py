import os
import time
from collections.abc import Sequence

import boto3
from tqdm import tqdm

from wisp.config.constants import (
    WIREGUARD_CLIENT_CONF_PATH,
    WIREGUARD_CLIENT_NAME,
    WIREGUARD_DNS1,
    WIREGUARD_DNS2,
    WIREGUARD_INTERFACE,
    WIREGUARD_IPV4,
    WIREGUARD_IPV6,
    WIREGUARD_KEY_PATH,
    WIREGUARD_KEYS_DIR,
)
from wisp.config.settings import WispConfig
from wisp.providers.aws.constants import DEFAULT_REGION
from wisp.providers.aws.pulumi import create_ec2_instance
from wisp.providers.base import BaseProvider, DeployVMResult, ProgressCallback
from wisp.schemas import InventoryContext
from wisp.utils import (
    create_or_select_pulumi_stack,
    get_public_ip,
    logger,
)
from wisp.wireguard import (
    configure_remote_server,
    connect_wireguard_client,
    disconnect_wireguard_client,
)


class AWSProvider(BaseProvider):
    """AWS implementation of :class:`~wisp.providers.base.BaseProvider`.

    Uses the Pulumi Automation API to provision/destroy an EC2 instance, Paramiko
    (SSH/SFTP) to configure the remote WireGuard server, and the local daemon to
    connect the client tunnel.
    """

    def __create_pulumi_program(
        self,
        region: str,
        force_current_ip: bool = False,
        wireguard_port: int | None = None,
    ) -> None:
        """Build the Pulumi program closure passed to the automation stack.

        Treats a non-positive ``wireguard_port`` as "use a random port".
        """
        create_ec2_instance(
            region,
            force_current_ip=force_current_ip,
            wireguard_port=wireguard_port
            if (wireguard_port and wireguard_port > 0)
            else None,
        )

    def get_available_regions(self) -> Sequence[str]:
        """List enabled AWS regions via ``ec2.describe_regions`` (boto3)."""
        client = boto3.client("ec2", region_name=DEFAULT_REGION)
        return [r["RegionName"] for r in client.describe_regions()["Regions"]]

    def deploy_vm(
        self,
        region: str,
        force_current_ip: bool = False,
        config: WispConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> DeployVMResult:
        """Provision an EC2 VM, configure WireGuard, and connect the client.

        Runs ``pulumi up``, waits ``config.vm_boot_timeout`` seconds for boot,
        writes the SSH/WireGuard private key locally (``0600``), configures
        the remote server via SSH/SFTP, and finally connects the local WireGuard
        client via the daemon.

        Args:
            region (str): Target region.
            force_current_ip (bool): Restrict access to the caller's public IP.
            config (WispConfig | None): Session config; a default is created if
                ``None`` (in which case ``force_current_ip`` seeds it).
            on_progress (ProgressCallback | None): Optional progress callback.

        Returns:
            DeployVMResult: The deployed instance's id, public/private IP, and
            WireGuard port.
        """
        logger.info(f"Deploying VM in region '{region}'...")

        if config is None:
            config = WispConfig(force_current_ip=force_current_ip)
        else:
            force_current_ip = config.force_current_ip

        if on_progress:
            on_progress("Aprovisionando infraestructura en AWS con Pulumi...", 0.05)

        logger.debug("Creating and deploying Pulumi stack...")
        stack = create_or_select_pulumi_stack(
            lambda: self.__create_pulumi_program(
                region,
                force_current_ip=force_current_ip,
                wireguard_port=config.wireguard_port
                if config.wireguard_port > 0
                else None,
            )
        )  # type: ignore
        up_result = stack.up()

        timeout_seconds = config.vm_boot_timeout
        logger.debug(
            f"Waiting for {timeout_seconds} "
            "seconds for the stack to be fully deployed..."
        )
        if on_progress:
            for elapsed in range(timeout_seconds):
                time.sleep(1)
                fraction = 0.25 + 0.50 * ((elapsed + 1) / timeout_seconds)
                on_progress(
                    f"Iniciando VM y servicios SSH ({elapsed + 1}/{timeout_seconds}s)...",
                    fraction,
                )
        else:
            for _ in tqdm(
                range(timeout_seconds),
                desc="Waiting for stack to deploy",
            ):
                time.sleep(1)

        outputs = up_result.outputs
        instance_id = outputs["instance_id"].value
        public_ip = outputs["instance_public_ip"].value
        private_ip = outputs["instance_private_ip"].value
        private_key = outputs["instance_private_key"].value
        wireguard_port = int(outputs["wireguard_port"].value)
        ssh_user = outputs["ssh_user"].value
        logger.debug(
            f"Deployed VM '{instance_id}' at '{public_ip}' with SSH user '{ssh_user}'"
        )

        if on_progress:
            on_progress("Configurando claves SSH...", 0.78)

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
        template_context = InventoryContext(
            ssh_user=ssh_user,
            instance_ip=public_ip,
            ssh_key_file=WIREGUARD_KEY_PATH,
            wireguard_port=wireguard_port,
            allowed_ips=allowed_ips,
            wireguard_public_ip=public_ip,
            wireguard_interface=WIREGUARD_INTERFACE,
            wireguard_ipv4=WIREGUARD_IPV4,
            wireguard_ipv6=WIREGUARD_IPV6,
            wireguard_dns1=WIREGUARD_DNS1,
            wireguard_dns2=WIREGUARD_DNS2,
            wireguard_client_name=WIREGUARD_CLIENT_NAME,
            wireguard_client_ipv4="",
            wireguard_client_ipv6="",
            wireguard_skip_client="n",
        )

        if on_progress:
            on_progress("Instalando y configurando WireGuard vía SSH...", 0.85)

        # Configure the remote WireGuard server and the local WireGuard client
        configure_remote_server(template_context)
        connect_wireguard_client(WIREGUARD_CLIENT_CONF_PATH.read_text())

        if on_progress:
            on_progress("¡VPN desplegada y activa!", 1.0)

        return DeployVMResult(
            instance_id=instance_id,
            public_ip=public_ip,
            private_ip=private_ip,
            wireguard_port=wireguard_port,
        )

    def delete_vm(
        self, region: str, on_progress: ProgressCallback | None = None
    ) -> int:
        """Disconnect the client, destroy the stack, and remove local artifacts.

        Brings the local tunnel down via the daemon, runs ``pulumi destroy``, and
        deletes the rendered inventory, private key, and client config if present.

        Args:
            region (str): Region whose stack should be destroyed.
            on_progress (ProgressCallback | None): Optional progress callback.

        Returns:
            int: Number of deleted resources (``0`` if the destroy failed).
        """
        logger.info(f"Deleting VM in region '{region}'...")

        logger.debug("Disconnecting WireGuard client...")
        disconnect_wireguard_client()

        stack = create_or_select_pulumi_stack(
            lambda: self.__create_pulumi_program(region)
        )  # type: ignore

        logger.debug("Destroying Pulumi stack...")
        try:
            destroy_result = stack.destroy()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error destroying stack: {e}")
            return 0

        # Remove the WireGuard related files if they exist
        logger.debug("Removing WireGuard related files...")
        if WIREGUARD_KEY_PATH.exists():
            os.remove(WIREGUARD_KEY_PATH)
            logger.debug(f"Removed WireGuard key file: {WIREGUARD_KEY_PATH}")

        if WIREGUARD_CLIENT_CONF_PATH.exists():
            os.remove(WIREGUARD_CLIENT_CONF_PATH)
            logger.debug(
                f"Removed WireGuard client config file: {WIREGUARD_CLIENT_CONF_PATH}"
            )

        if on_progress:
            on_progress("Recursos destruidos exitosamente.", 1.0)

        return destroy_result.summary.resource_changes.get("delete", 0)  # type: ignore
