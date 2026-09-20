# Installation

## Requirements

- Linux/macOS host for the client (the daemon uses systemd socket activation on
  Linux, or a native Windows service + Named Pipes on Windows; the macOS adapter
  is not implemented yet — see `MacOSAdapter`
  in [`daemon/adapter.py`](../src/wisp/daemon/adapter.py)).
- **Python 3.14+** (see `.python-version` and `requires-python` in
  `pyproject.toml`).
- **WireGuard tools** (`wg`, `wg-quick`) on the client — installed by `setup.sh`
  (Linux/macOS) or `setup.ps1` (Windows).
- **Pulumi CLI** — installed by `setup.sh` (Linux/macOS) or `setup.ps1` (Windows)
  unless `--skip-pulumi` is passed.
- **Cloud credentials** available in the environment (for example via the AWS
  CLI, `~/.aws/credentials`, or `~/.oci/config`), with permissions to manage
  instances, security rules, and key pairs, **or** configured in `wisp.toml`.

## Installing the CLI

Install the package as an editable tool so the `wisp` command is available:

```bash
uv tool install --editable .
```

## Installing the privileged daemon

### Linux/macOS

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
2. `installWireGuardClient` — installs WireGuard tools for the detected OS and
   verifies `wg` is available (shared helper from `scripts/utils.sh`).
3. `ensureCurl` — installs `curl` if missing (needed to fetch Pulumi).
4. `installPulumi` — detects Pulumi in the root or invoking user's environment;
   if it is missing, installs it for the invoking user under `~/.pulumi`
   (skipped with `--skip-pulumi`).
5. `removeExistingInstallation` — stops and disables the previous service and
   socket, removes their systemd unit files and clears the old daemon files.
6. `createWispGroup` — creates the `wisp` group and adds the invoking user
   (`$SUDO_USER`) to it. This group gates access to the daemon socket.
7. `installDaemonFiles` — copies `src/` to `/usr/local/lib/wisp/src` and creates
   an isolated virtualenv at `/usr/local/lib/wisp/venv`.
8. `installSystemdUnits` — installs `wisp.socket` and `wisp.service`, reloads
   systemd, and enables/starts the socket.

> After running `setup.sh`, log out and back in (or run `newgrp wisp`) so your
> new `wisp` group membership takes effect. Until then, connecting to the daemon
> socket fails with a `PermissionError`.

### Windows

The installation is performed with `setup.ps1`, which installs WireGuard Windows
exe, Pulumi via `winget`, and a native Windows service for the daemon.

The `setup.ps1` script performs the following steps:

1. Requires administrator privileges.
2. Installs `uv` if not already present.
3. Installs Pulumi via `winget`.
4. Installs WireGuard Windows exe.
5. Creates the `wisp` local group and adds the current user to it.
6. Copies the source code and Python dependencies to the installation directory.
7. Installs the Python virtual environment and Wisp into it.
8. Installs the Wisp Windows service.
9. Starts the Wisp service.

The daemon supports both systemd socket activation (Linux) and Windows Named
Pipes (`WindowsNamedPipeTransport`) for communication with the CLI/TUI.

## Python dependencies

Declared in `pyproject.toml`:

- `pulumi` (`>=3,<4`) and `pulumi-aws` (`>=7,<8`) — infrastructure provisioning.
- `pulumi-oci` (`>=4.22.0`) — OCI provider support.
- `pulumi-tls` — generates the RSA 4096 key pair for SSH.
- `boto3` — lists available AWS regions.
- `oci` — OCI SDK (regions, credentials).
- `paramiko` — SSH/SFTP remote server configuration.
- `textual` — the terminal UI.
- `tqdm` — CLI-mode progress bar.

## Runtime directories

These are created/populated at runtime and are gitignored:

| Path | Contents |
| ------ | ---------- |
| `keys/wireguard-key.pem` | SSH/WireGuard private key (`0600` on Linux/macOS, icacls on Windows) |
| `wireguard-confs/wg0-client.conf` | Client config fetched from the VM |
| `logs/wisp.log` | Rotating log (5 MB × 5 backups) |

Paths are all derived from the repository root in
`src/wisp/config/constants.py`.
