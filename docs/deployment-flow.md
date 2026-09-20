# Deployment flow

This document walks through what happens on deploy and destroy, mapping each
step to the code that performs it.

## Deploy

Entry: `Provider.deploy_vm(region, force_current_ip=False, config=None, on_progress=None)`
(`providers/pulumi_base.py`, shared by all Pulumi-based providers — `aws` and
`oci` today; see `ProviderEnum` for the current list).

1. **Resolve config.** If `config` is `None`, a `WispConfig` is built from the
   `[general]` TOML section via `load_wisp_config()` (and the `force_current_ip`
   argument, when true, overrides it); otherwise `force_current_ip` is taken
   from the provided config.

2. **Provision with Pulumi.** `create_or_select_pulumi_stack(program, provider=...)`
   selects (or creates) the provider-specific stack (`wisp-stack-aws` or
   `wisp-stack-oci`) in project `wisp-project`, then `stack.up()` runs the
   provider-specific program:
   - `ensure_plugins()` installs the provider plugins (`aws` `v7.44.0`,
     `oci` `v4.22.0`, `tls` `v5.5.1`) once per process.
   - The provider program declares the infrastructure: for AWS,
     `create_ec2_instance` (security group + EC2 instance); for OCI,
     `create_oci_instance` (VCN, Internet Gateway, Route Table, Security List,
     Subnet + Compute Instance). Both open UDP for the WireGuard port and
     TCP 22 for SSH, generate an RSA 4096 key pair via `tls.PrivateKey`, and
     export the stack outputs.
   - Stack **outputs**: `instance_id`, `instance_public_ip`,
     `instance_private_ip`, `instance_private_key`, `wireguard_port`, `ssh_user`.

3. **Wait for boot.** Sleeps `config.vm_boot_timeout` seconds (default 60),
   reporting progress via `on_progress` (TUI) or `tqdm` (CLI).

4. **Persist the private key.** Reads the `instance_private_key` output and writes
   it to `keys/wireguard-key.pem` with mode `0600` (Linux/macOS) or secured via
   `icacls` with well-known SIDs (Windows).

5. **Compute AllowedIPs.** `<your-ip>/32` if `force_current_ip`, else
   `0.0.0.0/0,::/0`.

6. **Configure the remote server.** `configure_remote_server(context)`
   (`wireguard/remote_server.py`) runs:
   - Establishes SSH connection to the VM using the private key (Paramiko,
     supporting Ed25519, ECDSA, RSA key formats).
   - Uploads `scripts/wireguard-server-install.sh` via SFTP to
     `/tmp/wireguard-install.sh` (this script **is not optional** — it is the
     WireGuard server installer, based on `angristan/wireguard-install`).
   - Executes the script remotely with configuration passed as environment variables:
     `SERVER_PUB_IP`, `SERVER_PORT`, `ALLOWED_IPS`, `SERVER_WG_NIC`,
     `SERVER_WG_IPV4`, `SERVER_WG_IPV6`, `CLIENT_DNS_1`, `CLIENT_DNS_2`,
     `AUTO_INSTALL=y`, `CLIENT_NAME`, `CLIENT_WG_IPV4`, `CLIENT_WG_IPV6`,
     `SKIP_CLIENT_CREATION`
   - The script installs WireGuard non-interactively, configures the interface,
     firewall, routing, and generates the client configuration
   - Downloads the generated client config (`wg0-client-*.conf`) via SFTP to
     `wireguard-confs/wg0-client.conf`

7. **Connect the local client.** `connect_wireguard_client(conf_text)`
   (`wireguard/local_client.py`) sends a `CONNECT` request with the config
   content to the daemon over `/run/wisp.sock` (Linux/macOS) or
   `\\.\pipe\wisp` (Windows). The daemon (`daemon/server.py`) writes the
   WireGuard config (`0600` / icacls) and runs `wg-quick up wg0` (Linux/macOS)
   or the native Windows equivalent via its adapter.

8. **Return.** A `DeployVMResult` with `instance_id`, `public_ip`, `private_ip`,
   and `wireguard_port`.

## Destroy

Entry: `Provider.delete_vm(region, on_progress=None)`.

1. **Disconnect the client.** `disconnect_wireguard_client()` sends a
   `DISCONNECT` request; the daemon runs `wg-quick down wg0` (Linux/macOS) or
   the native Windows equivalent.

2. **Destroy infrastructure.** Selects the stack and calls `stack.destroy()`.
   Errors are logged and cause an early return of `0`.

3. **Clean up local artifacts** (if present):
   - `keys/wireguard-key.pem`
   - `wireguard-confs/wg0-client.conf`

4. **Return** the number of deleted resources
   (`destroy_result.summary.resource_changes["delete"]`, defaulting to `0`).

## Notes on the remote installer

`scripts/wireguard-server-install.sh` is a non-interactive WireGuard server
installer (based on the widely used `angristan/wireguard-install`, MIT). It is
driven entirely by environment variables set by the SSH/SFTP orchestration, so
no interactive prompts are needed. `scripts/utils.sh` holds shared shell helpers
(`isRoot`, `checkOS`, `installPackages`, `installWireGuardClient`,
`uninstallWg`) used by both the server and client install scripts.

## Operating system differences in the deployment flow

- **Linux/macOS**: The daemon listens on `/run/wisp.sock`. The client connects
  via Unix domain socket. The server script is executed with `sudo`.
- **Windows**: The daemon listens on the Named Pipe `\\.\pipe\wisp`. The client
  connects via `WindowsNamedPipeTransport`. The server script is still uploaded
  via SFTP and executed, but paths and permissions differ (`icacls` with SIDs
  instead of `chmod 600`).
