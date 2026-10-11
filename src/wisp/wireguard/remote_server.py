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


def _connect_ssh(
    ssh_user: str, instance_ip: str, ssh_key_file: str
) -> paramiko.SSHClient:
    """Open an SSH connection to a server, authenticated by public key.

    Tries to load the private key as Ed25519, ECDSA, then RSA (OpenSSH or
    PKCS#8). When ``ssh_key_file`` is empty, connects without an explicit key
    so Paramiko falls back to the SSH agent and default key locations.

    Args:
        ssh_user (str): User to connect as.
        instance_ip (str): Server hostname or IP.
        ssh_key_file (str): Path to the user's private key, or ``""`` for
            agent/default-key authentication.

    Returns:
        paramiko.SSHClient: The connected client; the caller owns it.

    Raises:
        paramiko.SSHException: When the key cannot be loaded or the
            connection fails.
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    key = None
    if ssh_key_file:
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

    try:
        ssh.connect(
            hostname=instance_ip,
            username=ssh_user,
            pkey=key,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
        )
    except Exception:
        ssh.close()
        raise
    logger.debug(f"SSH connection established to {ssh_user}@{instance_ip}")
    return ssh


def _run_remote(ssh: paramiko.SSHClient, command: str) -> tuple[int, str, str]:
    """Run a command on the server and return its exit status and output.

    Args:
        ssh (paramiko.SSHClient): The connected SSH client.
        command (str): Shell command to execute.

    Returns:
        tuple[int, str, str]: Exit status, stdout, and stderr.
    """
    _, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    return exit_status, stdout.read().decode(), stderr.read().decode()


def remove_wisp_server_configs(
    ssh_user: str,
    instance_ip: str,
    ssh_key_file: str = "",
    on_progress: Callable[[str, float | None], None] | None = None,
) -> bool:
    """Tear down every Wisp-created WireGuard interface on a remote server.

    Wisp names its server-side interfaces ``wisp-<hex>``, so only files
    matching ``/etc/wireguard/wisp-*.conf`` are touched — a pre-existing
    ``wg0.conf`` (or any non-Wisp config) is left alone. For each match the
    interface is brought down first: ``wg-quick down`` runs the config's
    ``PostDown`` rules, which removes the iptables/firewall rules the
    installer added. Packages are intentionally kept — the server may have
    been using WireGuard before Wisp.

    Args:
        ssh_user (str): User to connect as (needs sudo/root).
        instance_ip (str): Server hostname or IP.
        ssh_key_file (str): Path to the user's private key, or ``""`` for
            agent/default-key authentication.
        on_progress (Callable[[str, float | None], None] | None): Optional
            progress callback.

    Returns:
        bool: True when the cleanup ran (even with zero matches); False when
        the SSH connection or the cleanup commands failed.
    """

    def _report(message: str, progress: float | None = None) -> None:
        if on_progress is not None:
            on_progress(message, progress)

    _report("Connecting to server over SSH...")
    try:
        ssh = _connect_ssh(ssh_user, instance_ip, ssh_key_file)
    except Exception as exc:
        logger.warning(f"Could not SSH to {instance_ip} for cleanup: {exc}")
        _report(f"Server cleanup skipped (SSH failed): {exc}", 1.0)
        return False

    try:
        _report("Removing Wisp WireGuard config from the server...", 0.6)
        # Glob our configs: the pattern only matches Wisp-created files.
        # "echo" + glob keeps this POSIX-shell safe (no ls parsing).
        _, listing = _run_remote(ssh, "echo /etc/wireguard/wisp-*.conf")
        listing = listing.strip()
        nics = []
        if listing and "*" not in listing:
            nics = [
                path.removeprefix("/etc/wireguard/").removesuffix(".conf")
                for path in listing.splitlines()
                if path.strip()
            ]

        for nic in nics:
            logger.info(f"Tearing down Wisp interface '{nic}' on {instance_ip}")
            # Best effort per interface: a missing/failed step for one config
            # must not stop the rest of the cleanup.
            _run_remote(ssh, f"wg-quick down {nic} 2>/dev/null || true")
            _run_remote(
                ssh,
                f"systemctl disable --now wg-quick@{nic} 2>/dev/null || true",
            )
            _run_remote(ssh, f"rm -f /etc/wireguard/{nic}.conf")

        if nics:
            _report(f"Removed {len(nics)} Wisp interface(s) from the server.", 0.9)
        else:
            _report("No Wisp interfaces found on the server.", 0.9)
        return True
    finally:
        ssh.close()
        logger.debug("SSH connection closed")


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

    ssh = _connect_ssh(ssh_user, instance_ip, str(ssh_key_file) if ssh_key_file else "")
    _report("Connected to server over SSH.")

    try:
        # Upload the install script via SFTP
        _report("Uploading WireGuard installer to the server...")
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
        _report("Installing WireGuard on the server (this may take several minutes)...")

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
                # Kept in memory for the failure message below; raw lines are
                # deliberately NOT logged — they are pure apt progress noise.
                seen_lines.append(line)
                now = time.monotonic()
                if now - last_report >= 1.0:
                    last_report = now
                    _report(line, None)

        seen_lines: list[str] = []
        _stream_installer_output()
        exit_status = stdout.channel.recv_exit_status()
        stderr_text = stderr.read().decode()

        if exit_status != 0:
            # Keep the last lines around: they usually carry the actual
            # apt/shell error when the install fails.
            tail = "\n".join(seen_lines[-30:])
            raise RuntimeError(
                f"WireGuard installation script failed with exit code {exit_status}. "
                f"Stderr: {stderr_text}\nLast installer output:\n{tail}"
            )

        logger.info("WireGuard server installation completed successfully")

        # Wait a moment for the client config file to be created
        time.sleep(2)
        _report("Downloading client configuration...")

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
