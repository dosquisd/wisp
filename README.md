# Wisp

**Ephemeral WireGuard VPNs on your own cloud.**

Wisp spins up a throwaway VM at a cloud provider (currently AWS and OCI),
installs and configures a WireGuard server on it, connects your local machine
as a WireGuard client, and tears everything down again on demand. Drive it
through an interactive terminal UI (TUI) or non-interactive CLI subcommands.

```text
   Wisp CLI/TUI ──Pulumi──▶ Cloud VM (AWS EC2 / OCI Compute + WireGuard)
        │  ▲                        │
        │  └──── Paramiko (SSH) ────┘   installs & configures the server
        ▼
   wisp daemon (privileged) ──wg-quick──▶ local WireGuard interface (wg0)
```

The client-side privileged daemon means the unprivileged CLI/TUI never needs
`sudo` to bring the local tunnel up or down; it talks to the daemon over a
group-restricted Unix socket (Linux/macOS) or Named Pipe (Windows) instead.

## Requirements

- Linux/macOS host for the client (the daemon uses systemd socket activation and
  `wg-quick` on Linux, or a native Windows service + Named Pipes on Windows;
  the macOS adapter is not implemented yet — see `MacOSAdapter`
  in [`daemon/adapter.py`](src/wisp/daemon/adapter.py)).
- Python 3.14+ (see `.python-version` and `requires-python` in
  `pyproject.toml`).
- WireGuard tools (`wg`, `wg-quick`) on the client — installed by `setup.sh`
  (Linux/macOS) or the WireGuard Windows installer via `setup.ps1` (Windows).
- Pulumi CLI — installed by `setup.sh` (Linux/macOS) or `setup.ps1` (Windows)
  unless `--skip-pulumi` is passed.
- Cloud credentials (AWS or OCI) available in the environment (for example via
  the AWS CLI, `~/.aws/credentials`, or `~/.oci/config`), or configured in
  `wisp.toml`.

> **Note:** As of this writing, Wisp ships with support for `aws` and `oci`.
> The provider layer is designed to be extensible — new providers can be added
> by implementing `BaseProvider` (or extending `PulumiProvider`) and
> registering them in `PROVIDERS_MAP`
> ([`src/wisp/providers/__init__.py`](src/wisp/providers/__init__.py)).
> For the current list, see `ProviderEnum`
> ([`src/wisp/providers/base.py`](src/wisp/providers/base.py)).

## Install

Install the CLI:

```bash
uv tool install --editable .
```

Install the privileged local daemon (needs root/administrator):

```bash
sudo ./setup.sh            # Linux/macOS; or: sudo ./setup.sh --skip-pulumi
./setup.ps1                # Windows (self-elevates to administrator)
```

Then log out and back in (or `newgrp wisp`) so your `wisp` group membership takes
effect. See [docs/installation.md](docs/installation.md) for details.

## Usage

```bash
wisp                          # launch the interactive TUI
wisp deploy aws --region eu-west-1   # deploy a VPN in a region
wisp deploy oci               # use the default region from [oci] in wisp.toml
wisp destroy aws --region eu-west-1  # destroy it and clean up
wisp regions aws               # list available regions
```

See [docs/usage.md](docs/usage.md) for the full CLI and TUI reference.

## Documentation

Full documentation lives in [`docs/`](docs/README.md):

- [Architecture](docs/architecture.md)
- [Installation](docs/installation.md)
- [Usage](docs/usage.md)
- [Configuration](docs/configuration.md)
- [Deployment flow](docs/deployment-flow.md)
- [Security model](docs/security.md)
- [Components reference](docs/components/README.md)
- [Contributing](docs/contributing.md)
