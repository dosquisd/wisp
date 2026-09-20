# Security model

## Privilege separation via the daemon

The client-side WireGuard interface requires root to bring up/down. Rather than
running the whole application as root, Wisp splits privileges:

- The **unprivileged frontend** (CLI/TUI) runs as your user.
- A **privileged daemon** (`wisp.service`, socket-activated by `wisp.socket` on
  Linux; native Windows Service via pywin32 on Windows) performs the privileged
  operations (`wg-quick up/down`, writing the WireGuard config).

They communicate over a Unix domain socket at `/run/wisp.sock` (Linux/macOS) or
a Named Pipe (`\\.\pipe\wisp`) on Windows.

### Socket access control

From `packaging/wisp.socket` (Linux):

- `SocketMode=0660`
- `SocketUser=root`
- `SocketGroup=wisp`

Only root and members of the `wisp` group can connect. `setup.sh` creates the
`wisp` group and adds the installing user (`setup.ps1` does the equivalent on
Windows with a local group). Group membership requires a re-login
(or `newgrp wisp`) to take effect; until then, connecting to the daemon raises a
`PermissionError` with guidance.

On Windows, the Named Pipe security descriptor grants full control to SYSTEM
and built-in Administrators, and read/write to the `wisp` group — implemented
with well-known SIDs in `daemon/transport.py`.

### Protocol

`daemon/protocol.py` defines a minimal newline-delimited JSON protocol:

- `Request { action: connect|disconnect|status, config_content?: str }`
- `Response { ok: bool, message: str }`

The daemon (`daemon/server.py`) handles one request per connection and dispatches
to the platform adapter for `connect` / `disconnect` / `status`.

> Note: the daemon writes whatever `config_content` it receives to the WireGuard
> config file and brings the interface up. Access to the socket/pipe is
> therefore equivalent to control over the local WireGuard interface — which is
> why it is restricted to the `wisp` group.

## Keys and secrets

- A fresh **RSA 4096 key pair** is generated per deployment via `pulumi-tls`. The
  private key is a Pulumi stack output.
- The private key is written locally to `keys/wireguard-key.pem` with mode
  `0600` (Linux/macOS) or secured via `icacls` with well-known SIDs (Windows),
  and used as the SSH key for the remote server configuration.
- On destroy, the key file and client config are removed.
- `keys/*.pem` and `wireguard-confs/*.conf` are gitignored so secrets are not
  committed.

## Firewall exposure

The security group (AWS) or security list (OCI) opens:

- UDP up to the WireGuard port (the tunnel).
- TCP 22 (SSH, for the remote server configuration).
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
| ---------- | ----------- | ------- |
| User ↔ daemon | Unix socket `0660 root:wisp` (Linux/macOS) or Named Pipe with SIDs (Windows) | Group-gated privileged control |
| Local ↔ VM | SSH with generated RSA 4096 key | Key stored `0600`/icacls, removed on destroy |
| Internet ↔ VM | Cloud security group/list | Optionally pinned to your `/32` |
| Cloud API | Your cloud credentials/environment | Wisp does not manage credentials; uses default chain or `wisp.toml` config |

## Operational cautions

- Destroying via `wisp destroy` removes the cloud resources and local secrets;
  the local key is not recoverable afterwards.
- The default `0.0.0.0/0` ingress means a deployed-but-forgotten VM is publicly
  reachable. Destroy stacks you no longer use.
