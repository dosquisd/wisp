# Deployment flow

This document walks through what happens on deploy and destroy, mapping each
step to the code that performs it.

## Deploy

Entry: `AWSProvider.deploy_vm(region, force_current_ip=False, config=None, on_progress=None)`
(`providers/aws/provider.py`).

1. **Resolve config.** If `config` is `None`, a `WispConfig(force_current_ip=...)`
   is created; otherwise `force_current_ip` is taken from the config.

2. **Provision with Pulumi.** `create_or_select_pulumi_stack(program)` selects (or
   creates) the `wisp-stack` stack in project `wisp-project`, then `stack.up()`
   runs the program `create_ec2_instance(region, ...)`:
   - `ensure_plugins()` installs the Pulumi `aws` (`v7.44.0`) and `tls`
     (`v5.5.1`) plugins once per process.
   - `get_ami()` selects the most recent Ubuntu AMI (owner Canonical) in the
     region.
   - `get_security_group()` opens:
     - UDP `0`→`wireguard_port` (the tunnel),
     - TCP `0`→`22` (SSH),
     - all egress.
     Ingress CIDR is `<your-ip>/32` when `force_current_ip`, else `0.0.0.0/0`.
   - A `tls.PrivateKey` (ED25519) is generated and its OpenSSH public key becomes
     an `aws.ec2.KeyPair`.
   - An `aws.ec2.Instance` (`t3.micro` by default) is created with that key and
     security group.
   - Stack **outputs**: `instance_id`, `instance_public_ip`,
     `instance_private_ip`, `instance_private_key`, `wireguard_port`, `ssh_user`.

3. **Wait for boot.** Sleeps `config.vm_boot_timeout` seconds (default 60),
   reporting progress via `on_progress` (TUI) or `tqdm` (CLI).

4. **Persist the private key.** Reads the `instance_private_key` output and writes
   it to `keys/wireguard-key.pem` with mode `0600`.

5. **Compute AllowedIPs.** `<your-ip>/32` if `force_current_ip`, else
   `0.0.0.0/0,::/0`.

6. **Configure the remote server.** `configure_remote_server(context)`
   (`wireguard/remote_server.py`) runs:
   - Establishes SSH connection to the VM using the private key
   - Uploads `scripts/wireguard-install.sh` via SFTP to `/tmp/wireguard-install.sh`
   - Executes the script remotely with configuration passed as environment variables:
     `SERVER_PUB_IP`, `SERVER_PORT`, `ALLOWED_IPS`, `SERVER_WG_NIC`,
     `SERVER_WG_IPV4`, `SERVER_WG_IPV6`, `CLIENT_DNS_1`, `CLIENT_DNS_2`,
     `AUTO_INSTALL=y`, `CLIENT_NAME`, `CLIENT_WG_IPV4`, `CLIENT_WG_IPV6`,
     `SKIP_CLIENT_CREATION`
   - The script (`scripts/wireguard-install.sh`) installs WireGuard non-interactively,
     configures the interface, firewall (firewalld or iptables), routing, and generates
     the client configuration
   - Downloads the generated client config (`wg0-client-*.conf`) via SFTP to
     `wireguard-confs/wg0-client.conf`

7. **Connect the local client.** `connect_wireguard_client(conf_text)`
   (`wireguard/local_client.py`) sends a `CONNECT` request with the config
   content to the daemon over `/run/wisp.sock`. The daemon
   (`daemon/server.py`) writes `/etc/wireguard/wg0.conf` (`0600`) and runs
   `wg-quick up wg0`.

8. **Return.** A `DeployVMResult` with `instance_id`, `public_ip`, `private_ip`,
   and `wireguard_port`.

## Destroy

Entry: `AWSProvider.delete_vm(region, on_progress=None)`.

1. **Disconnect the client.** `disconnect_wireguard_client()` sends a
   `DISCONNECT` request; the daemon runs `wg-quick down wg0`.

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
driven entirely by environment variables set by the SSH/SFTP orchestration,
so no interactive prompts are needed. `scripts/utils.sh` holds shared shell helpers
(`isRoot`, `checkOS`, `installPackages`, `installWireGuardClient`,
`uninstallWg`) used by both the server and client install scripts.