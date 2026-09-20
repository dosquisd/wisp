# `wisp.wireguard`

Orchestrates the remote WireGuard server (via Paramiko SSH/SFTP) and the local
client (via the privileged daemon).

## `wireguard/remote_server.py`

### `configure_remote_server(inventory_context: InventoryContext) -> None`

Configures the remote WireGuard server using Paramiko (SSH/SFTP):

1. Establishes an SSH connection to the VM using the private key, trying
   multiple key classes (`Ed25519Key`, `ECDSAKey`, `RSAKey` — OpenSSH or
   PKCS#8 formats).
2. Uploads `scripts/wireguard-server-install.sh` via SFTP to
   `/tmp/wireguard-install.sh` and makes it executable.
3. Executes the script remotely with `sudo` (via a pseudo-terminal), passing
   the configuration as environment variables: `SERVER_PUB_IP`, `SERVER_PORT`,
   `ALLOWED_IPS`, `SERVER_WG_NIC`, `SERVER_WG_IPV4`, `SERVER_WG_IPV6`,
   `CLIENT_DNS_1`, `CLIENT_DNS_2`, `AUTO_INSTALL=y`, `CLIENT_NAME`,
   `CLIENT_WG_IPV4`, `CLIENT_WG_IPV6`, `SKIP_CLIENT_CREATION`.
4. Locates the generated client config (`wg0-client-*.conf`, with a fallback to
   the SSH user's home directory) and downloads it via SFTP to
   `wireguard-confs/wg0-client.conf`.

See [deployment flow](../deployment-flow.md#deploy).

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
