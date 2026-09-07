# Wisp Documentation

Wisp provisions **ephemeral WireGuard VPNs on your own cloud**. It spins up a
throwaway virtual machine at a cloud provider (currently AWS), installs and
configures a WireGuard server on it via Ansible, connects your local machine as
a WireGuard client through a privileged daemon, and tears everything down again
on demand.

Wisp can be driven either through an interactive terminal UI (TUI) or through
non-interactive CLI subcommands.

## Documentation index

| Document | Contents |
|----------|----------|
| [Architecture](./architecture.md) | High-level design, module map, runtime data flow |
| [Installation](./installation.md) | System requirements, `setup.sh`, systemd daemon, dependencies |
| [Usage](./usage.md) | CLI subcommands and the interactive TUI |
| [Configuration](./configuration.md) | `WispConfig`, constants, environment assumptions |
| [Deployment flow](./deployment-flow.md) | Step-by-step of deploy and destroy |
| [Components](./components/README.md) | Per-module reference (providers, wireguard, daemon, cli, utils) |
| [Security model](./security.md) | Keys, firewall rules, socket permissions, trust boundaries |
| [Contributing](./contributing.md) | Adding a provider, code layout, style |

## Quick mental model

```
        ┌─────────────┐     Pulumi Automation API      ┌──────────────────┐
        │  Wisp CLI/  │ ─────────────────────────────► │   AWS EC2 (VM)    │
        │  TUI (user) │                                 │  Ubuntu + SSH     │
        └──────┬──────┘                                 └────────┬─────────┘
               │                                                 │
               │  Ansible (SSH) runs WireGuard installer         │
               │ ───────────────────────────────────────────────►
               │                                                 │
               │  Fetches generated wg0-client.conf back         │
               │ ◄───────────────────────────────────────────────
               │
               │  Unix socket /run/wisp.sock
               ▼
        ┌──────────────┐   wg-quick up/down wg0   ┌──────────────────┐
        │ wisp daemon  │ ───────────────────────► │ local WireGuard  │
        │ (root, systemd)                         │ interface wg0    │
        └──────────────┘                          └──────────────────┘
```

The client-side privileged daemon exists so the unprivileged CLI/TUI never needs
`sudo` to bring the local WireGuard interface up or down; it talks to the daemon
over a group-restricted Unix socket instead.
