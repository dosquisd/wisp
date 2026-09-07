# Installation

## Requirements

- **Linux** host for the client (the daemon uses systemd socket activation and
  `wg-quick`). The repository's shell scripts support Debian/Ubuntu, Fedora,
  CentOS/AlmaLinux/Rocky, Oracle Linux, Arch, and Alpine.
- **Python 3.14+** (see `.python-version` and `requires-python` in
  `pyproject.toml`).
- **WireGuard tools** (`wg`, `wg-quick`) on the client — installed by `setup.sh`.
- **Pulumi CLI** — installed by `setup.sh` unless `--skip-pulumi` is passed.
- **AWS credentials** available in the environment (for example via the AWS CLI
  or environment variables), with permissions to manage EC2 instances, security
  groups, and key pairs.
- **`ansible-playbook`** available either globally or in the project virtualenv
  (`ansible-core` is a declared dependency).

## Python dependencies

Declared in `pyproject.toml`:

- `pulumi` (`>=3,<4`) and `pulumi-aws` (`>=7,<8`) — infrastructure provisioning.
- `pulumi-tls` — generates the ED25519 key pair for SSH.
- `ansible-core` — configures the remote WireGuard server.
- `boto3` — lists available AWS regions.
- `jinja2` — renders the Ansible inventory template.
- `textual` — the terminal UI.
- `tqdm` — CLI-mode progress bar.

The project uses [`uv`](https://docs.astral.sh/uv/) (there is a `uv.lock`). A
console script entry point `wisp = "wisp.main:main"` is defined.

## Installing the CLI

Install the package as an editable tool so the `wisp` command is available:

```bash
uv tool install --editable .
```

## Installing the privileged daemon (`setup.sh`)

The client-side daemon must run as root so it can bring the local WireGuard
interface up and down. `setup.sh` installs it. **Run it as root** (it checks and
exits otherwise):

```bash
sudo ./setup.sh
# or, to skip installing Pulumi (e.g. it is already installed):
sudo ./setup.sh --skip-pulumi
```

What `setup.sh` does, in order:

1. `initialCheck` — asserts it is running as root and detects the OS.
2. `ensureCurl` — installs `curl` if missing (needed to fetch Pulumi).
3. `installWireGuardClient` — installs WireGuard tools for the detected OS and
   verifies `wg` is available.
4. `installPulumi` — installs Pulumi into `/usr/local/lib/wisp/pulumi` and links
   `/usr/local/bin/pulumi` (skipped with `--skip-pulumi` or if already present).
5. `createWispGroup` — creates the `wisp` group and adds the invoking user
   (`$SUDO_USER`) to it. This group gates access to the daemon socket.
6. `installDaemonFiles` — copies `src/` to `/usr/local/lib/wisp/src` and creates
   an isolated virtualenv at `/usr/local/lib/wisp/venv`.
7. `installSystemdUnits` — installs `wisp.socket` and `wisp.service`, reloads
   systemd, and enables/starts the socket.

> After running `setup.sh`, log out and back in (or run `newgrp wisp`) so your
> new `wisp` group membership takes effect. Until then, connecting to the daemon
> socket fails with a `PermissionError`.

## systemd units

`packaging/wisp.socket`:

- Listens on `/run/wisp.sock`.
- `SocketMode=0660`, `SocketUser=root`, `SocketGroup=wisp` — only root and
  members of `wisp` can connect.

`packaging/wisp.service`:

- `Requires=wisp.socket` (socket-activated).
- Runs `python -m wisp.daemon.server` as `User=root` from
  `/usr/local/lib/wisp/src/`.

The daemon supports both systemd socket activation (`LISTEN_FDS` / fd 3) and, for
local development, creating the socket directly at `SOCKET_PATH`.

## Runtime directories

These are created/populated at runtime and are gitignored:

| Path | Contents |
|------|----------|
| `keys/wireguard-key.pem` | SSH/WireGuard private key (mode `0600`) |
| `inventory/inventory.ini` | Rendered Ansible inventory |
| `wireguard-confs/wg0-client.conf` | Client config fetched from the VM |
| `logs/wisp.log` | Rotating log (5 MB × 5 backups) |

Paths are all derived from the repository root in
`src/wisp/config/constants.py`.
