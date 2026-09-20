# Configuration

Configuration is loaded from `wisp.toml` (user-level and project-level merged —
user-level overrides project-level). Per-session deployment settings live in the
`WispConfig` dataclass, built from the `[general]` TOML section, and
defaults/paths are constants.

## `WispConfig` (`config/settings.py`)

A dataclass holding per-session, per-deployment settings. Defaults come from
`config/constants.py`; any field omitted in the `[general]` TOML section falls
back to those constants.

| Field | Type | Default | Meaning |
| ------- | ------ | --------- | --------- |
| `vm_boot_timeout` | `int` | `60` | Seconds to wait for the VM to boot / SSH to come up before configuring WireGuard |
| `wireguard_interface` | `str` | `"wg0"` | WireGuard interface name |
| `wireguard_ipv4` | `str` | `"10.66.66.1"` | Server-side WireGuard IPv4 |
| `wireguard_ipv6` | `str` | `"fd42:42:42::1"` | Server-side WireGuard IPv6 |
| `wireguard_dns1` | `str` | `"1.1.1.1"` | Primary DNS pushed to the client |
| `wireguard_dns2` | `str` | `"1.0.0.1"` | Secondary DNS pushed to the client |
| `wireguard_port` | `int` | `0` | UDP port; `0` means a random port in `49152–65535` |
| `force_current_ip` | `bool` | `False` | If true, restrict firewall/AllowedIPs to your current public IP (`/32`) |

The TUI Configuration screen edits these values in memory; the CLI uses the
TOML-derived defaults (with `force_current_ip` overridable through the provider
call).

### `force_current_ip` behaviour

- **Security rules**: when true, ingress `cidr_blocks` is `["<your-ip>/32"]`;
  otherwise `["0.0.0.0/0"]`.
- **Client AllowedIPs**: when true, `allowed_ips` is `"<your-ip>/32"`; otherwise
  `"0.0.0.0/0,::/0"` (route all traffic through the tunnel).

Your current public IP is looked up via `https://api.ipify.org`
(`utils.get_public_ip`).

## Constants (`config/constants.py`)

### Tags and Pulumi identity

| Constant | Value | Use |
| ---------- | ------- | ----- |
| `CREATED_BY_TAG` | `"wisp"` | Value for the `created-by` tag |
| `DEFAULT_TAG` | `{"created-by": "wisp"}` | Applied to all cloud resources |
| `PULUMI_PROJECT_NAME` | `"wisp-project"` | Pulumi project |
| `get_pulumi_stack_name(provider)` | `"wisp-stack-<provider>"` | Provider-specific Pulumi stack (e.g. `wisp-stack-aws`, `wisp-stack-oci`) |
| `DEFAULT_VM_BOOT_TIMEOUT_SECONDS` | `60` | Default `vm_boot_timeout` |

### Paths

`ROOTDIR` is resolved by walking up from the current working directory until it
finds a `pyproject.toml` anchor, falling back to the file location of
`constants.py` if not found.

| Constant | Path (relative to repo root) |
| ---------- | ------------------------------ |
| `WIREGUARD_SCRIPT_PATH` | `scripts/wireguard-server-install.sh` |
| `WIREGUARD_KEYS_DIR` | `keys/` |
| `WIREGUARD_KEY_PATH` | `keys/wireguard-key.pem` |
| `WIREGUARD_CLIENT_CONF_PATH` | `wireguard-confs/wg0-client.conf` |
| `WISP_CONFIG_FILE_NAME` | `wisp.toml` |
| `WISP_PROJECT_CONFIG_PATH` | `<repo root>/wisp.toml` |
| `WISP_USER_CONFIG_PATH` | `~/.config/wisp/wisp.toml` (Linux), `~/Library/Application Support/wisp/wisp.toml` (macOS), `%APPDATA%\wisp\wisp.toml` (Windows) |

Both config file paths are created (empty) and secured at import time if they do
not exist.

### WireGuard defaults

`WIREGUARD_INTERFACE="wg0"`, `WIREGUARD_IPV4="10.66.66.1"`,
`WIREGUARD_IPV6="fd42:42:42::1"`, `WIREGUARD_DNS1="1.1.1.1"`,
`WIREGUARD_DNS2="1.0.0.1"`, `WIREGUARD_CLIENT_NAME=""`.

## AWS constants (`providers/aws/constants.py`)

| Constant | Value |
| ---------- | ------- |
| `DEFAULT_REGION` | `"us-east-2"` |
| `DEFAULT_EC2_INSTANCE_TYPE` | `"t3.micro"` |
| `DEFAULT_AMI_NAME` | `ubuntu/images/hvm-ssd-gp3/ubuntu-resolute-26.04-amd64-server-20260619` |
| `DEFAULT_AMI_OWNER` | `"099720109477"` (Canonical) |

> The default AMI is region-dependent; the code selects the most recent AMI
> matching the name filter and owner in the target region.

## OCI constants (`providers/oci/constants.py`)

| Constant | Value |
| ---------- | ------- |
| `DEFAULT_COMPARTMENT_ID` | `""` (empty → defaults to tenancy OCID) |
| `DEFAULT_SHAPE` | `"VM.Standard.A1.Flex"` |
| `DEFAULT_OCPUS` | `2.0` |
| `DEFAULT_MEMORY_IN_GBS` | `8.0` |
| `DEFAULT_IMAGE_OS` | `"Canonical Ubuntu"` |
| `DEFAULT_IMAGE_OS_VERSION` | `"24.04"` |
| `DEFAULT_VCN_CIDR` | `"10.0.0.0/16"` |
| `DEFAULT_SUBNET_CIDR` | `"10.0.0.0/24"` |
| `DEFAULT_DNS_LABEL` | `"wispvcn"` |
| `DEFAULT_SUBNET_DNS_LABEL` | `"wispsubnet"` |
| `DEFAULT_SECURITY_LIST_NAME` | `"wisp-security-list"` |
| `DEFAULT_ROUTE_TABLE_NAME` | `"wisp-route-table"` |
| `DEFAULT_INTERNET_GATEWAY_NAME` | `"wisp-internet-gateway"` |
| `DEFAULT_VCN_NAME` | `"wisp-vcn"` |
| `DEFAULT_SUBNET_NAME` | `"wisp-subnet"` |
| `DEFAULT_INSTANCE_NAME_PREFIX` | `"wisp-instance"` |
| `DEFAULT_KEY_PAIR_NAME` | `"wisp-key-pair"` |

## Daemon / protocol constants

- `UnixSocketTransport.SOCKET_PATH = "/run/wisp.sock"` (`daemon/transport.py`).
- `WindowsNamedPipeTransport.PIPE_NAME = r"\\.\pipe\wisp"` (`daemon/transport.py`).
- Random WireGuard port range: `49152–65535` (`utils/randoms.py`,
  `get_wireguard_port`).

## Logging

`utils/logger.py` configures a `wisp` logger with:

- A rotating file handler at `logs/wisp.log` (5 MB per file, 5 backups), level
  `DEBUG`.
- A console (stderr) handler at level `ERROR` by default. In CLI mode,
  `main.py` raises this handler to `DEBUG`.

## File permissions by operating system

- **Linux/macOS**: `secure_file()` sets permissions to `0600` (owner-only).
- **Windows**: Uses `icacls` with well-known SIDs (`*S-1-5-18:F` for SYSTEM,
  `*S-1-5-32-544:F` for Administrators) because account names
  ("Administrators", "SYSTEM") are localized on non-English Windows
  installations, which makes `icacls` fail to resolve them by name.

## Provider configuration (`wisp.toml`)

Per-provider settings are stored in the `[aws]` and `[oci]` sections of
`wisp.toml` (the providers supported today; see `ProviderEnum`
([`src/wisp/providers/base.py`](../src/wisp/providers/base.py)) for the
current list). These sections are optional; if omitted, the provider SDK uses
its default credential chain.

### `[aws]` section

| Field | Type | Default | Meaning |
| ------- | ------ | --------- | --------- |
| `region` | `str` | `AWS_DEFAULT_REGION` | AWS region for deployments |
| `profile` | `str` | `""` | AWS CLI profile name (e.g. `"default"`, `"work"`) |
| `access_key_id` | `str` | `""` | Explicit access key (prefer `profile`) |
| `secret_access_key` | `str` | `""` | Explicit secret key (prefer `profile`) |
| `session_token` | `str` | `""` | Session token for temporary credentials |

### `[oci]` section

| Field | Type | Default | Meaning |
| ------- | ------ | --------- | --------- |
| `region` | `str` | `""` (SDK default) | OCI region for deployments (e.g. `"sa-bogota-1"`) |
| `profile` | `str` | `"DEFAULT"` | Profile name in `~/.oci/config` |
| `tenancy_ocid` | `str` | `""` | Tenancy OCID |
| `user_ocid` | `str` | `""` | User OCID |
| `fingerprint` | `str` | `""` | API signing key fingerprint |
| `private_key_path` | `str` | `""` | Path to API signing key (PEM) |
| `compartment_ocid` | `str` | `OCI_DEFAULT_COMPARTMENT_ID` | Compartment OCID (defaults to tenancy) |

All fields are optional. When omitted, wisp falls back to the provider's
standard CLI/SDK credential chain:

- **AWS**: env vars, `~/.aws/credentials`, `~/.aws/config`, IAM roles
- **OCI**: `~/.oci/config` profile, env vars (`OCI_TENANCY`, `OCI_USER`,
  `OCI_FINGERPRINT`, `OCI_PRIVATE_KEY_PATH`, `OCI_REGION`)

> **Important**: There is **no cross-provider default region**. Each provider
> has its own configured region (`[aws].region`, `[oci].region`), which is used
> when `-r/--region` is not supplied on the CLI.
