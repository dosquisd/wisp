# Configuration

Wisp configuration is code-defined. There is no config file; per-session
settings live in memory (`WispConfig`), and defaults/paths are constants.

## `WispConfig` (`config/settings.py`)

A dataclass holding per-session, per-deployment settings. Defaults come from
`config/constants.py`.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `ansible_timeout` | `int` | `60` | Seconds to wait for the VM to boot / SSH to come up before running Ansible |
| `wireguard_interface` | `str` | `"wg0"` | WireGuard interface name |
| `wireguard_ipv4` | `str` | `"10.66.66.1"` | Server-side WireGuard IPv4 |
| `wireguard_ipv6` | `str` | `"fd42:42:42::1"` | Server-side WireGuard IPv6 |
| `wireguard_dns1` | `str` | `"1.1.1.1"` | Primary DNS pushed to the client |
| `wireguard_dns2` | `str` | `"1.0.0.1"` | Secondary DNS pushed to the client |
| `wireguard_port` | `int` | `0` | UDP port; `0` means a random port in `49152–65535` |
| `force_current_ip` | `bool` | `False` | If true, restrict firewall/AllowedIPs to your current public IP (`/32`) |

The TUI Configuration screen edits these values; the CLI uses defaults (with
`force_current_ip` overridable through the provider call).

### `force_current_ip` behaviour

- **Security group**: when true, ingress `cidr_blocks` is `["<your-ip>/32"]`;
  otherwise `["0.0.0.0/0"]`.
- **Client AllowedIPs**: when true, `allowed_ips` is `"<your-ip>/32"`; otherwise
  `"0.0.0.0/0,::/0"` (route all traffic through the tunnel).

Your current public IP is looked up via `https://api.ipify.org`
(`utils.get_public_ip`).

## Constants (`config/constants.py`)

### Tags and Pulumi identity

| Constant | Value | Use |
|----------|-------|-----|
| `CREATED_BY_TAG` | `"wisp"` | Value for the `created-by` tag |
| `DEFAULT_TAG` | `{"created-by": "wisp"}` | Applied to all AWS resources |
| `PULUMI_STACK_NAME` | `"wisp-stack"` | Pulumi stack |
| `PULUMI_PROJECT_NAME` | `"wisp-project"` | Pulumi project |
| `DEFAULT_ANSIBLE_PLAYBOOK_TIMEOUT_SECONDS` | `60` | Default `ansible_timeout` |

### Paths (all derived from `ROOTDIR`)

`ROOTDIR` is resolved from the file location
(`src/wisp/config/constants.py` → three parents up = repo root).

| Constant | Path (relative to repo root) |
|----------|------------------------------|
| `WIREGUARD_SCRIPT_PATH` | `scripts/wireguard-install.sh` |
| `WIREGUARD_PLAYBOOK_PATH` | `ansible/wireguard_install.yaml` |
| `WIREGUARD_INVENTORY_TEMPLATE_PATH` | `templates/inventory.ini.j2` |
| `WIREGUARD_INVENTORY_PATH` | `inventory/inventory.ini` |
| `WIREGUARD_KEYS_DIR` | `keys/` |
| `WIREGUARD_KEY_PATH` | `keys/wireguard-key.pem` |
| `WIREGUARD_CLIENT_CONF_PATH` | `wireguard-confs/wg0-client.conf` |

### WireGuard defaults

`WIREGUARD_INTERFACE="wg0"`, `WIREGUARD_IPV4="10.66.66.1"`,
`WIREGUARD_IPV6="fd42:42:42::1"`, `WIREGUARD_DNS1="1.1.1.1"`,
`WIREGUARD_DNS2="1.0.0.1"`, `WIREGUARD_CLIENT_NAME=""`.

## AWS constants (`providers/aws/constants.py`)

| Constant | Value |
|----------|-------|
| `DEFAULT_REGION` | `"us-east-2"` |
| `DEFAULT_EC2_INSTANCE_TYPE` | `"t3.micro"` |
| `DEFAULT_AMI_NAME` | `ubuntu/images/hvm-ssd-gp3/ubuntu-resolute-26.04-amd64-server-...` |
| `DEFAULT_AMI_OWNER` | `"099720109477"` (Canonical) |

> The default AMI is region-dependent; the code selects the most recent AMI
> matching the name filter and owner in the target region.

## Daemon / protocol constants

- `SOCKET_PATH = "/run/wisp.sock"` (`daemon/protocol.py`).
- `WG_CONF_PATH = /etc/wireguard/wg0.conf` (`daemon/server.py`).
- Random WireGuard port range: `49152–65535` (`utils/randoms.py`,
  `get_wireguard_port`).

## Logging

`utils/logger.py` configures a `wisp` logger with:

- A rotating file handler at `logs/wisp.log` (5 MB per file, 5 backups), level
  `DEBUG`.
- A console (stderr) handler at level `ERROR` by default. In CLI mode,
  `main.py` raises this handler to `DEBUG`.
