# Architecture

## Overview

Wisp is a Python application (package `wisp`, source under `src/wisp/`) that
orchestrates three cooperating pieces:

1. A **frontend** — an interactive Textual TUI or argparse-based CLI — that the
   user drives.
2. A **cloud provider layer** that uses the Pulumi Automation API to provision
   and destroy infrastructure, plus Ansible to configure the remote host.
3. A **privileged local daemon** that manages the client-side WireGuard
   interface without requiring the user to run the whole application as root.

## Package layout

```
src/wisp/
├── main.py             # Entry point; argparse CLI + TUI dispatch
├── schemas.py          # InventoryContext TypedDict (Ansible template vars)
├── cli/                # Textual TUI
│   ├── app.py          # WispApp (global styles, screen registration)
│   ├── state.py        # AppState (in-memory session state)
│   ├── __main__.py     # `python -m wisp.cli` launcher
│   └── screens/        # MainMenu, Config, Deploy, Progress screens
├── config/             # Configuration
│   ├── settings.py     # WispConfig dataclass (per-session config)
│   └── constants.py    # Paths, tags, WireGuard defaults
├── providers/          # Cloud provider abstraction
│   ├── base.py         # BaseProvider ABC + result TypedDicts
│   └── aws/            # AWS implementation (provider, pulumi program, constants)
├── wireguard/          # Client/server WireGuard orchestration
│   ├── local_client.py # Talks to the daemon over the Unix socket
│   └── remote_server.py# Runs the Ansible playbook against the VM
├── daemon/             # Privileged local daemon
│   ├── server.py       # asyncio Unix-socket server (runs as root)
│   └── protocol.py     # Request/Response wire format + socket path
└── utils/              # Helpers: logging, Pulumi/Ansible resolution, templates, RNG
```

Supporting non-Python assets at the repository root:

```
ansible/    wireguard_install.yaml   # Playbook that configures the remote server
scripts/    *.sh                     # WireGuard install/uninstall + shared shell utils
templates/  inventory.ini.j2         # Jinja2 Ansible inventory template
packaging/  wisp.service, wisp.socket# systemd units for the daemon
keys/       (runtime)                # Generated SSH/WireGuard private key (gitignored)
inventory/  (runtime)                # Rendered Ansible inventory (gitignored)
wireguard-confs/ (runtime)           # Fetched client config (gitignored)
logs/       (runtime)                # Rotating log files (gitignored)
```

## Runtime components and boundaries

| Component | Privilege | Where it runs | Responsibility |
|-----------|-----------|---------------|----------------|
| CLI / TUI | user | local | Collect config, trigger deploy/destroy, show progress |
| Provider (AWS) | user (uses AWS creds) | local | Pulumi up/destroy, render inventory, invoke Ansible |
| Pulumi program | user | local process | Declare EC2 instance, security group, TLS key pair |
| Ansible playbook | remote root (via SSH) | remote VM | Install & configure WireGuard server, fetch client conf |
| wisp daemon | root | local (systemd) | `wg-quick up/down wg0` on the local machine |

The **trust boundary** worth noting: the unprivileged frontend never runs
`wg-quick` directly. Instead it sends a request to the daemon over
`/run/wisp.sock`. The socket is owned by `root:wisp` with mode `0660`, so any
user in the `wisp` group can control the local tunnel, but only root's daemon
actually mutates `/etc/wireguard/wg0.conf` and brings the interface up.

## End-to-end data flow (deploy)

```
User → TUI/CLI
  → AWSProvider.deploy_vm(region, config)
      → Pulumi Automation: create_or_select_stack(program).up()
          program = create_ec2_instance(...)
            - get_ami() (most recent Ubuntu AMI)
            - get_security_group() (UDP wg port + TCP 22)
            - tls.PrivateKey (ED25519) → aws.ec2.KeyPair
            - aws.ec2.Instance
            - exports: instance_id, public/private ip, private_key, wg_port, ssh_user
      → wait `ansible_timeout` seconds for SSH/boot
      → write private key to keys/wireguard-key.pem (0600)
      → render templates/inventory.ini.j2 → inventory/inventory.ini
      → configure_remote_server(context)
            → ansible-playbook -i inventory ansible/wireguard_install.yaml
                - copies + runs scripts/wireguard-server-install.sh (non-interactive)
                - fetches wg0-client-*.conf → wireguard-confs/wg0-client.conf
      → connect_wireguard_client(conf_text)
            → daemon: write /etc/wireguard/wg0.conf (0600) + `wg-quick up wg0`
  → returns DeployVMResult(instance_id, public_ip, private_ip, wireguard_port)
```

## End-to-end data flow (destroy)

```
User → TUI/CLI
  → AWSProvider.delete_vm(region)
      → disconnect_wireguard_client()  → daemon: `wg-quick down wg0`
      → Pulumi Automation: stack.destroy()
      → remove local artifacts: inventory.ini, wireguard-key.pem, wg0-client.conf
  → returns count of deleted resources
```

## Provider abstraction

All providers implement `BaseProvider` (`providers/base.py`):

- `get_available_regions() -> Sequence[str]`
- `deploy_vm(region, force_current_ip=False, config=None, on_progress=None) -> DeployVMResult`
- `delete_vm(region, on_progress=None) -> int`

`ProviderEnum` and `PROVIDERS_MAP` in `providers/__init__.py` map a provider name
(`"aws"`) to its concrete class. Adding a new provider means implementing
`BaseProvider` and registering it in `PROVIDERS_MAP`. See
[Contributing](./contributing.md).

The `on_progress` callback (`Callable[[str, float | None], None]`) lets the TUI's
`ProgressScreen` render live progress; in pure CLI mode it is `None` and a `tqdm`
progress bar is used for the boot wait instead.
