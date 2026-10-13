<div align="center">

```text
██╗    ██╗██╗███████╗██████╗
██║    ██║██║██╔════╝██╔══██╗
██║ █╗ ██║██║███████╗██████╔╝
██║███╗██║██║╚════██║██╔═══╝
╚███╔███╔╝██║███████║██║
 ╚══╝╚══╝ ╚═╝╚══════╝╚═╝
```

**A VPN for the sessions you actually need.**

A monthly subscription bills you for every minute of the month so you can use
thirty. Wisp spins up a WireGuard server in your own cloud account, connects
you, and destroys it when you're done — measured: **~30 seconds to a working
tunnel** on your own VPS, ~2–3 minutes on a cloud provider (the VM boot is
the slow part), and a typical session costs fractions of a cent on
pay-as-you-go pricing.

<img src=".github/assets/demo-tui.gif" alt="Wisp TUI — deploy, tunnel, destroy" width="100%">

[![Python](https://img.shields.io/badge/python-3.14%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-10b981)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows-64748b)](docs/installation.md)
[![Providers](https://img.shields.io/badge/providers-aws%20%7C%20oci%20%7C%20gcp%20%7C%20vps-f59e0b)](#supported-providers)

[Installation](#install) · [Quick start](#quick-start) · [Documentation](docs/README.md) · [Contributing](docs/contributing.md)

</div>

---

## Why Wisp

| | Subscription VPN | Always-on VPS | Wisp |
| --- | --- | --- | --- |
| Billing | Flat, monthly | 24/7, whether you use it or not | Per session — fractions of a cent |
| Who runs the server | The provider | You | You, briefly |
| Upkeep | None | Patches, a box to forget | None — it's destroyed |
| Exit IP | Shared pool | Dedicated, tied to your account | Dedicated, tied to your account |

**Who it's for:** developers who already have a cloud account (or a spare VPS)
and use a VPN occasionally — a few sessions a month, not all day every day.

**Who it's not for:** if you need an anonymous exit IP, look elsewhere — Wisp's
exit IP belongs to *your* cloud account or *your* VPS, which is the point.

- **Designed so nothing outlives your session.** The VM is destroyed on exit —
  `q`, `Ctrl+C`, closing the terminal — and an optional TTL watchdog tears down
  forgotten sessions. (The watchdog timer runs on your machine: if that machine
  is off or suspended when the TTL expires, the session survives until the next
  `wisp gc` — and `wisp gc --destroy` cleans up anything a crash left behind.)
- **Nothing to clean up by hand.** Orphan detection and `wisp gc` catch
  anything a crash left behind.
- **Bring your own server.** Already have a VPS? Skip the cloud entirely —
  Wisp configures WireGuard on it over SSH and cleans up after itself.
- **No sudo at runtime.** The privileged daemon owns the local WireGuard
  interface; the CLI/TUI never elevate after installation.

## Features

| | Feature | What it means |
| --- | --- | --- |
| **TUI** | Interactive terminal UI | Full deploy wizard, live progress, one-key teardown |
| **CLI** | Scriptable subcommands | `deploy`, `destroy`, `regions`, `gc` — JSON output, `tqdm` progress |
| **Multi-cloud** | AWS · OCI · GCP | Provisioned via Pulumi; RSA 4096 SSH keys per session |
| **BYO server** | Custom VPS | No cloud account needed — SSH into a host you own |
| **Ephemeral** | Session guard | `q`/`Ctrl+C`/`esc`/signals/`atexit` all release the resources, exactly once |
| **Watchdog** | TTL auto-destroy | Optional OS-level timer runs `wisp destroy` if the session outlives its TTL |
| **Garbage collection** | `wisp gc` | Finds and destroys leftover stacks from crashed sessions |
| **No sudo at runtime** | Privileged daemon | After installation the CLI/TUI never elevate; a local daemon owns `wg-quick` |
| **Live installer output** | Progress streaming | The remote WireGuard install streams into the progress bar — no frozen screens |

## How it works

```text
   Wisp CLI/TUI ──Pulumi──▶ Cloud VM (AWS EC2 / OCI Compute / GCP + WireGuard)
        │  ▲                        │
        │  └──── Paramiko (SSH) ────┘   installs & configures the server
        ▼
   wisp daemon (privileged) ──wg-quick──▶ local WireGuard interface (wg0)
```

The client-side privileged daemon means the unprivileged CLI/TUI never needs
`sudo` to bring the local tunnel up or down; it talks to the daemon over a
group-restricted Unix socket (Linux) or Named Pipe (Windows) instead. The
session guard arms *before* provisioning starts, so a crashed TUI still
leaves a marker behind — the next run offers to clean it up, and the optional
TTL watchdog handles it even if nobody reopens Wisp.

## Install (from source)

Requirements: Python **3.14+** (if you install via `uv`, it manages Python for
you — you never see this requirement), the
[Pulumi CLI](https://www.pulumi.com/docs/install/), and WireGuard tools — both
installed by the setup script.

```bash
# 0. Clone and enter the repo
git clone https://github.com/dosquisd/wisp.git && cd wisp

# 1. Install the CLI (isolated tool venv)
uv tool install .

# 2. Install the privileged local daemon (needs root/administrator)
sudo ./setup.sh            # Linux; or: sudo ./setup.sh --skip-pulumi
./setup.ps1                # Windows (self-elevates to administrator)
```

Then log out and back in (or `newgrp wisp`) so your `wisp` group membership
takes effect. macOS is not supported yet (the daemon adapter is not
implemented — see `MacOSAdapter` in
[`daemon/adapter.py`](src/wisp/daemon/adapter.py)). A published PyPI package
with a one-command installer is planned.

## Quick start

```bash
# 1. Authenticate the Pulumi backend (the deployment state lives there)
pulumi login

# 2. Configure your cloud credentials (standard SDK chains — see docs)
aws configure               # or ~/.oci/config, or [gcp] in wisp.toml

# 3. Launch the TUI (or use the CLI directly)
wisp
```

```bash
# CLI equivalent — deploy, tunnel, destroy:
wisp deploy aws --region eu-west-1   # provisions VM + WireGuard, connects you
wisp destroy aws --region eu-west-1  # tears it all down
```

<!-- TODO: record the CLI demo GIF — deploy + destroy, 15-20s.
<img src=".github/assets/demo-cli.gif" alt="wisp deploy / destroy on the CLI" width="100%">
-->

## CLI cheat sheet

| Command | What it does |
| --- | --- |
| `wisp` | Launch the interactive TUI |
| `wisp deploy <provider> [-r region]` | Deploy a VPN (add `--ttl 120`, `--wireguard-port 51820`) |
| `wisp deploy vps --host <ip> --ssh-user root` | Configure WireGuard on a server you own |
| `wisp destroy <provider> [-r region]` | Tear down the tunnel + all cloud resources |
| `wisp regions <provider>` | List available regions (JSON) |
| `wisp gc [--refresh] [--destroy]` | Find and clean up leftover stacks |

## Supported providers

| Provider | Provisioning | Credentials |
| --- | --- | --- |
| **AWS** | Pulumi (`t3.micro`, most-recent Ubuntu AMI) | Standard AWS chain (`aws configure`, env vars) |
| **OCI** | Pulumi (`VM.Standard.A1.Flex`, Ubuntu 24.04) | `~/.oci/config` profile |
| **GCP** | Pulumi (SPOT `e2-micro`, default network) | Service account key or ADC |
| **Custom VPS** | None — SSH into a host you already own | Your own SSH key (`[vps]` in `wisp.toml`) |

> **Note:** as of this writing, Wisp ships with support for `aws`, `oci`,
> `gcp`, and `vps`. The provider layer is designed to be extensible — see
> `ProviderEnum`
> ([`src/wisp/providers/base.py`](src/wisp/providers/base.py)) and
> `PROVIDERS_MAP`
> ([`src/wisp/providers/__init__.py`](src/wisp/providers/__init__.py)), or
> the [contributing guide](docs/contributing.md#adding-a-cloud-provider) to
> add your own.

## Documentation

Full documentation lives in [`docs/`](docs/README.md):

| | |
| --- | --- |
| [Architecture](docs/architecture.md) | High-level design, module map, runtime data flow |
| [Installation](docs/installation.md) | System requirements, `setup.sh` / `setup.ps1`, daemon |
| [Usage](docs/usage.md) | Full CLI and TUI reference |
| [Configuration](docs/configuration.md) | `wisp.toml`, `WispConfig`, per-provider settings |
| [Deployment flow](docs/deployment-flow.md) | Step-by-step deploy and destroy |
| [Security model](docs/security.md) | Keys, firewall, socket permissions, trust boundaries |
| [Components reference](docs/components/README.md) | Per-module reference |
| [Contributing](docs/contributing.md) | Adding a provider, style, commits |

## Security

Keys are per-session RSA 4096 pairs, stored `0600` and removed on destroy.
The daemon socket is group-restricted (`root:wisp`). Cloud credentials are
never stored by Wisp — each provider uses its standard SDK chain (the only
file Wisp ever touches is the optional `[gcp].credentials_path`, which you
point at; Wisp reads it, it does not manage it). Read the full
[security model](docs/security.md).

## Contributing

PRs against `main`. The provider layer is the easiest entry point — see
[adding a cloud provider](docs/contributing.md#adding-a-cloud-provider).

## License

[MIT](LICENSE) — Copyright (c) 2026 Juan D. Perez
