"""Remote WireGuard server configuration via Paramiko (SSH/SFTP)."""

import re
import stat
import time
from collections.abc import Callable

import paramiko

from wisp.config.constants import (
    WIREGUARD_CLIENT_CONF_PATH,
    WIREGUARD_SCRIPT_PATH,
)
from wisp.schemas import InventoryContext
from wisp.utils import logger


def configure_remote_server(
    inventory_context: InventoryContext,
    on_progress: Callable[[str, float | None], None] | None = None,
) -> None:
    """
    Configure the remote WireGuard server using Paramiko (SSH/SFTP).

    Copies the install script to the remote server, executes it with the
    provided configuration via environment variables, and downloads the
    generated client configuration.

    Args:
        inventory_context (InventoryContext): Context containing variables for
            the WireGuard installation.
        on_progress (Callable[[str, float | None], None] | None): Optional
            callback receiving human-readable progress updates (message, and a
            percentage, or ``None`` while indeterminate). The installer output is
            streamed through it, throttled to one update per second, so a long
            install never looks like a hang.
    """

    # A namespace object can't be refreshed after `paramiko` connect; each
    # phase reports through this so screen code stays fully decoupled.
    def _report(message: str, progress: float | None = None) -> None:
        if on_progress is not None:
            on_progress(message, progress)

    ssh_user = inventory_context["ssh_user"]
    instance_ip = inventory_context["instance_ip"]
    ssh_key_file = inventory_context["ssh_key_file"]
    wireguard_port = inventory_context["wireguard_port"]
    allowed_ips = inventory_context["allowed_ips"]
    wireguard_public_ip = inventory_context["wireguard_public_ip"]
    wireguard_interface = inventory_context["wireguard_interface"]
    wireguard_ipv4 = inventory_context["wireguard_ipv4"]
    wireguard_ipv6 = inventory_context["wireguard_ipv6"]
    wireguard_dns1 = inventory_context["wireguard_dns1"]
    wireguard_dns2 = inventory_context["wireguard_dns2"]
    wireguard_client_name = inventory_context["wireguard_client_name"]
    wireguard_client_ipv4 = inventory_context["wireguard_client_ipv4"]
    wireguard_client_ipv6 = inventory_context["wireguard_client_ipv6"]
    wireguard_skip_client = inventory_context["wireguard_skip_client"]

    logger.info(f"Configuring remote WireGuard server at {instance_ip} via SSH...")

    # Prepare environment variables for the remote script
    env_vars = {
        "SERVER_PUB_IP": wireguard_public_ip,
        "SERVER_PORT": str(wireguard_port),
        "ALLOWED_IPS": allowed_ips,
        "SERVER_WG_NIC": wireguard_interface,
        "SERVER_WG_IPV4": wireguard_ipv4,
        "SERVER_WG_IPV6": wireguard_ipv6,
        "CLIENT_DNS_1": wireguard_dns1,
        "CLIENT_DNS_2": wireguard_dns2,
        "AUTO_INSTALL": "y",
        "CLIENT_NAME": wireguard_client_name,
        "CLIENT_WG_IPV4": wireguard_client_ipv4,
        "CLIENT_WG_IPV6": wireguard_client_ipv6,
        "SKIP_CLIENT_CREATION": wireguard_skip_client,
    }

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    _report("Conectando al servidor por SSH...")

    try:
        # Connect via SSH using the private key (try multiple key types for PKCS#8/OpenSSH)
        key = None
        for key_class in (
            paramiko.Ed25519Key,
            paramiko.ECDSAKey,
            paramiko.RSAKey,
        ):
            try:
                key = key_class.from_private_key_file(str(ssh_key_file))
                logger.debug(f"Loaded SSH key as {key_class.__name__}")
                break
            except paramiko.SSHException:
                continue
        if key is None:
            raise paramiko.SSHException(
                f"Unable to load private key from {ssh_key_file}. "
                "Supported formats: Ed25519, ECDSA, RSA (OpenSSH or PKCS#8)"
            )

        ssh.connect(
            hostname=instance_ip,
            username=ssh_user,
            pkey=key,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
        )
        logger.debug(f"SSH connection established to {ssh_user}@{instance_ip}")

        # Upload the install script via SFTP
        _report("Cargando el instalador de WireGuard al servidor...")
        sftp = ssh.open_sftp()
        remote_script_path = "/tmp/wireguard-install.sh"
        sftp.put(str(WIREGUARD_SCRIPT_PATH), remote_script_path)

        # Make script executable
        sftp.chmod(
            remote_script_path,
            stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
        )
        sftp.close()
        logger.debug(f"Uploaded install script to {remote_script_path}")

        # Build the command with environment variables
        env_prefix = " ".join(f"{k}={v}" for k, v in env_vars.items())
        command = f"sudo {env_prefix} {remote_script_path}"
        logger.debug(f"Executing remote command: {command}")
        _report("Instalando WireGuard en el servidor (puede tardar varios minutos)...")

        # Execute the script with a pseudo-terminal for sudo
        stdin, stdout, stderr = ssh.exec_command(command, get_pty=True, timeout=300)

        # Stream the installer output in real-time. `recv_exit_status()` blocks
        # until the script exits and delivers *no* output while running, so a
        # minutes-long install would otherwise sit frozen on one status line.
        # Read lines as they arrive instead, throttling UI updates to one per
        # second (the installer floods progress bars for apt-get, etc.).
        last_report: float = time.monotonic()

        def _stream_installer_output() -> None:
            nonlocal last_report
            for raw in stdout:
                raw_text = (
                    raw.decode(errors="replace") if isinstance(raw, bytes) else raw
                )
                line = re.sub(
                    r"\x1b\[[0-9;?]*[A-Za-z]",
                    "",
                    raw_text.replace("\r", ""),
                ).strip()
                if not line:
                    continue
                logger.debug(line)
                now = time.monotonic()
                if now - last_report >= 1.0:
                    last_report = now
                    _report(line, None)

        _stream_installer_output()
        exit_status = stdout.channel.recv_exit_status()
        stdout_text = stdout.read().decode()
        stderr_text = stderr.read().decode()

        if stdout_text:
            logger.debug(f"Remote stdout:\n{stdout_text}")
        if stderr_text:
            logger.warning(f"Remote stderr:\n{stderr_text}")

        if exit_status != 0:
            raise RuntimeError(
                f"WireGuard installation script failed with exit code {exit_status}. "
                f"Stderr: {stderr_text}"
            )

        logger.info("WireGuard server installation completed successfully")

        # Wait a moment for the client config file to be created
        time.sleep(2)
        _report("Descargando la configuración del cliente...")

        # Download the client configuration via SFTP
        sftp = ssh.open_sftp()
        remote_conf_pattern = f"/root/{wireguard_interface}-client-*.conf"
        logger.debug(f"Looking for client config: {remote_conf_pattern}")

        # Find the generated client config file
        stdin, stdout, stderr = ssh.exec_command(
            f"ls -t {remote_conf_pattern} 2>/dev/null | head -1"
        )
        remote_conf_path = stdout.read().decode().strip()

        if not remote_conf_path:
            # Fallback: check home directory of ssh_user
            stdin, stdout, stderr = ssh.exec_command(
                f"ls -t /home/{ssh_user}/{wireguard_interface}-client-*.conf 2>/dev/null | head -1"
            )
            remote_conf_path = stdout.read().decode().strip()

        if not remote_conf_path:
            raise FileNotFoundError(
                "WireGuard client configuration file not found on remote server"
            )

        logger.debug(f"Downloading client config from {remote_conf_path}")
        sftp.get(remote_conf_path, str(WIREGUARD_CLIENT_CONF_PATH))
        sftp.close()

        logger.info(f"Client configuration downloaded to {WIREGUARD_CLIENT_CONF_PATH}")

    finally:
        ssh.close()
        logger.debug("SSH connection closed")
