# `wisp.wireguard`

Orchestrates the remote WireGuard server (via Paramiko SSH/SFTP) and the local
client (via the privileged daemon).

## `wireguard/remote_server.py`

### `_connect_ssh(ssh_user, instance_ip, ssh_key_file) -> paramiko.SSHClient`

Shared SSH connection helper. Tries to load the private key as Ed25519, ECDSA,
then RSA (OpenSSH or PKCS#8); when `ssh_key_file` is empty, connects without an
explicit key so Paramiko falls back to the SSH agent and default key
locations (the VPS flow). The client is closed on a failed connect.

### `configure_remote_server(inventory_context: InventoryContext) -> None`

Configures the remote WireGuard server using Paramiko (SSH/SFTP):

1. Establishes an SSH connection via `_connect_ssh`.
2. Uploads the packaged `wireguard-server-install.sh` (package data at
   `src/wisp/data/`) via SFTP to
   `/tmp/wireguard-install.sh` and makes it executable.
3. Executes the script remotely with `sudo` (via a pseudo-terminal), passing
   the configuration as environment variables: `SERVER_PUB_IP`, `SERVER_PORT`,
   `ALLOWED_IPS`, `SERVER_WG_NIC`, `SERVER_WG_IPV4`, `SERVER_WG_IPV6`,
   `CLIENT_DNS_1`, `CLIENT_DNS_2`, `AUTO_INSTALL=y`, `CLIENT_NAME`,
   `CLIENT_WG_IPV4`, `CLIENT_WG_IPV6`, `SKIP_CLIENT_CREATION`.
4. Locates the generated client config (`wg0-client-*.conf`, with a fallback to
   the SSH user's home directory) and downloads it via SFTP to
   `WISP_DATA_DIR/wireguard-confs/wg0-client.conf` (creating the parent
   directory first).

See [deployment flow](../deployment-flow.md#deploy).

### `remove_wisp_server_configs(ssh_user, instance_ip, ssh_key_file="", on_progress=None) -> bool`

Tears down every Wisp-created WireGuard interface on a remote server
(used by the VPS provider's `delete_vm`). For each
`/etc/wireguard/wisp-*.conf`: `wg-quick down <nic>` (the config's `PostDown`
rules remove the iptables/firewall rules the installer added),
`systemctl disable --now wg-quick@<nic>`, and deletion of the config file.
Only `wisp-*` files are matched — a pre-existing `wg0.conf` or any other
config is never touched, and packages are kept. Best effort per interface:
a failed step for one config does not stop the rest. Returns `False` when
the SSH connection or the listing fails.

## `wireguard/local_client.py`

Thin client that talks to the privileged daemon over the platform transport
(Unix socket on Linux, Named Pipe on Windows — selected by
`daemon.transport.get_transport()`).

- `connect_wireguard_client(config_content: str) -> Response` — `CONNECT` with
  the config body.
- `disconnect_wireguard_client() -> Response` — `DISCONNECT`.
- `status_wireguard_client() -> Response` — `STATUS`.

Each function sends one `Request` and returns its `Response`; the transport
raises a descriptive `PermissionError` if the socket cannot be connected
(typically missing `wisp` group membership).

## `InventoryContext` (`wisp.schemas`)

`TypedDict` of the variables consumed by `configure_remote_server`:
SSH user, instance IP, SSH key file, WireGuard port, allowed IPs, public IP,
interface, IPv4/IPv6, DNS 1/2, client name, client IPv4/IPv6, and
`skip_client`. Populated during deploy from the Pulumi stack outputs and the
active `WispConfig`.
