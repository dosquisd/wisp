# Wisp

**Ephemeral WireGuard VPNs on your own cloud.**

Wisp spins up a throwaway VM at a cloud provider (currently AWS), installs and
configures a WireGuard server on it, connects your local machine as a WireGuard
client, and tears everything down again on demand. Drive it through an
interactive terminal UI (TUI) or non-interactive CLI subcommands.

```
   Wisp CLI/TUI ──Pulumi──▶ AWS EC2 (Ubuntu + WireGuard)
        │  ▲                      │
        │  └────Ansible (SSH)─────┘   installs & configures the server
        ▼
   wisp daemon (root) ──wg-quick──▶ local WireGuard interface (wg0)
```

The client-side privileged daemon means the unprivileged CLI/TUI never needs
`sudo` to bring the local tunnel up or down; it talks to the daemon over a
group-restricted Unix socket instead.

## Requirements

- Linux host (systemd + `wg-quick`)
- Python 3.14+
- Pulumi CLI (installed by `setup.sh`)
- AWS credentials with permissions for EC2, security groups, and key pairs

## Install

Install the CLI:

```bash
uv tool install --editable .
```

Install the privileged local daemon (needs root):

```bash
sudo ./setup.sh            # or: sudo ./setup.sh --skip-pulumi
```

Then log out and back in (or `newgrp wisp`) so your `wisp` group membership takes
effect. See [docs/installation.md](docs/installation.md) for details.

## Usage

```bash
wisp                          # launch the interactive TUI
wisp deploy aws -r us-east-2   # deploy a VPN in a region
wisp destroy aws -r us-east-2  # destroy it and clean up
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

## License

The bundled WireGuard install script (`scripts/wireguard-server-install.sh`) is
based on [angristan/wireguard-install](https://github.com/angristan/wireguard-install)
(MIT).
