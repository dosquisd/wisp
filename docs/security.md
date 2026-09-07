# Security model

## Privilege separation via the daemon

The client-side WireGuard interface requires root to bring up/down. Rather than
running the whole application as root, Wisp splits privileges:

- The **unprivileged frontend** (CLI/TUI) runs as your user.
- A **root daemon** (`wisp.service`, socket-activated by `wisp.socket`) performs
  the privileged operations (`wg-quick up/down`, writing
  `/etc/wireguard/wg0.conf`).

They communicate over a Unix domain socket at `/run/wisp.sock`.

### Socket access control

From `packaging/wisp.socket`:

- `SocketMode=0660`
- `SocketUser=root`
- `SocketGroup=wisp`

Only root and members of the `wisp` group can connect. `setup.sh` creates the
`wisp` group and adds the installing user. Group membership requires a re-login
(or `newgrp wisp`) to take effect; until then, `local_client._send` raises a
`PermissionError` with guidance.

### Protocol

`daemon/protocol.py` defines a minimal newline-delimited JSON protocol:

- `Request { action: connect|disconnect|status, config_content?: str }`
- `Response { ok: bool, message: str }`

The daemon (`daemon/server.py`) handles one request per connection and dispatches
to `handle_connect` / `handle_disconnect` / `handle_status`.

> Note: the daemon writes whatever `config_content` it receives to
> `/etc/wireguard/wg0.conf` and runs `wg-quick`. Access to the socket is
> therefore equivalent to control over the local WireGuard interface — which is
> why the socket is restricted to the `wisp` group.

## Keys and secrets

- A fresh **ED25519 key pair** is generated per deployment via `pulumi-tls`. The
  private key is a Pulumi stack output.
- The private key is written locally to `keys/wireguard-key.pem` with mode
  `0600` and used as the SSH key for Ansible.
- On destroy, the key file, rendered inventory, and client config are removed.
- `keys/*.pem`, `inventory/inventory.ini`, and `wireguard-confs/*.conf` are
  gitignored so secrets are not committed.

## Firewall exposure

The EC2 security group opens:

- UDP up to the WireGuard port (the tunnel).
- TCP 22 (SSH, needed for Ansible).
- All egress.

Ingress source is controlled by `force_current_ip`:

- **`False` (default)**: `0.0.0.0/0` — reachable from anywhere.
- **`True`**: `<your current public IP>/32` — reachable only from your current
  IP. This tightens both SSH and the tunnel exposure, at the cost of breaking if
  your public IP changes.

Consider enabling `force_current_ip` for a tighter posture when your IP is
stable.

## Trust boundaries summary

| Boundary | Mechanism | Notes |
|----------|-----------|-------|
| User ↔ daemon | Unix socket `0660 root:wisp` | Group-gated privileged control |
| Local ↔ VM | SSH with generated ED25519 key | Key stored `0600`, removed on destroy |
| Internet ↔ VM | EC2 security group | Optionally pinned to your `/32` |
| AWS API | Your AWS credentials/environment | Wisp does not manage credentials |

## Operational cautions

- Destroying via `wisp destroy` removes the cloud resources and local secrets;
  the local key is not recoverable afterwards.
- The default `0.0.0.0/0` ingress means a deployed-but-forgotten VM is publicly
  reachable. Destroy stacks you no longer use.
