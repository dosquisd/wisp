# `wisp.providers`

Cloud provider abstraction with the AWS and OCI implementations.

> **Note:** As of this writing, Wisp ships with support for `aws` and `oci`.
> The provider layer is designed to be extensible — new providers can be added
> by implementing `BaseProvider` (or extending `PulumiProvider`) and
> registering them in `PROVIDERS_MAP`
> ([`src/wisp/providers/__init__.py`](../../src/wisp/providers/__init__.py)).
> For the current list, see `ProviderEnum`
> ([`src/wisp/providers/base.py`](../../src/wisp/providers/base.py)).

## `providers/__init__.py`

- `ProviderEnum(enum.Enum)`: `AWS = "aws"`, `OCI = "oci"`.
- `PROVIDERS_MAP: dict[ProviderEnum, type[BaseProvider]]`: maps the enum to the
  concrete provider class (`{ProviderEnum.AWS: AWSProvider, ProviderEnum.OCI: OCIProvider}`).

## `providers/base.py` — `BaseProvider` (ABC)

Result/callback types:

- `ProgressCallback = Callable[[str, float | None], None]`
- `CredentialError(RuntimeError)`: raised when provider credentials are invalid
  or missing.
- `DeployVMResult(TypedDict)`: `instance_id`, `public_ip`, `private_ip`,
  `wireguard_port`.

Abstract members:

| Member | Returns | Purpose |
| -------- | --------- | --------- |
| `__init__(credentials=None)` | — | Initialize with optional provider credentials |
| `credentials` (property) | `BaseCredentials` | Return the provider credentials |
| `get_available_regions()` | `Sequence[str]` | List provider regions |
| `deploy_vm(region, force_current_ip=False, config=None, on_progress=None)` | `DeployVMResult` | Provision + configure + connect |
| `delete_vm(region, on_progress=None)` | `int` | Disconnect + destroy + cleanup, returns deleted count |
| `_provider_name` (property) | `str` | Display name for progress messages |

## `providers/pulumi_base.py` — `PulumiProvider`

Shared deploy/destroy flow for Pulumi-based providers. `deploy_vm` resolves the
config (`load_wisp_config()` from TOML when `None`), creates/selects the
provider-specific stack, runs `stack.up()`, waits `config.vm_boot_timeout`
seconds, persists the SSH key, configures the remote server over SSH/SFTP
(`configure_remote_server`), and connects the local client through the daemon.
Subclasses implement `_create_pulumi_program(...)` and `get_available_regions()`.

## `providers/aws/`

### `constants.py`

`DEFAULT_REGION="us-east-2"`, `DEFAULT_EC2_INSTANCE_TYPE="t3.micro"`,
`DEFAULT_AMI_NAME` (Ubuntu, gp3), `DEFAULT_AMI_OWNER="099720109477"` (Canonical).

### `pulumi.py` — the Pulumi program

Module-level `_plugins_ready` flag guards `ensure_plugins()`, which installs the
`aws` (`v7.44.0`) and `tls` (`v5.5.1`) plugins once.

- `get_ami(region, owners=None, ami_names=None)` — most-recent AMI matching the
  name filter/owner.
- `get_default_username(ami_name)` — maps AMI family to default SSH user
  (`ubuntu`, `ec2-user`, `centos`, `admin`; fallback `ec2-user`).
- `get_security_group(region, force_current_ip=False, ...)` — builds the SG:
  ingress UDP `0`→`wireguard_port` and TCP `0`→`22`, all egress. CIDR is
  `<your-ip>/32` if `force_current_ip` else `0.0.0.0/0`. Random port if none
  given. Tagged with `DEFAULT_TAG`.
- `create_ec2_instance(region, /, force_current_ip=False, *, ...)` — the program
  passed to Pulumi. Creates the SG, an RSA 4096 `tls.PrivateKey`
  (`algorithm="RSA", rsa_bits=4096`), an `aws.ec2.KeyPair` from its OpenSSH
  public key, and the `aws.ec2.Instance`. Exports: `instance_id`,
  `instance_public_ip`, `instance_private_ip`, `instance_private_key`,
  `wireguard_port`, `ssh_user`.

### `provider.py` — `AWSProvider(PulumiProvider)`

- `credentials` (property) — the resolved `AWSCredentials`.
- `_create_pulumi_program(region, force_current_ip=False, wireguard_port=None)`
  — wraps `create_ec2_instance`; treats `wireguard_port <= 0` as "random".
- `get_available_regions()` — `boto3` `ec2.describe_regions()`; raises
  `CredentialError` if credentials are invalid.
- `_provider_name` — `"AWS"`.
- `deploy_vm(...)` / `delete_vm(...)` — shared flow, see
  [deployment flow](../deployment-flow.md).

## `providers/oci/`

### `constants.py`

Defaults for the OCI deployment: `DEFAULT_SHAPE="VM.Standard.A1.Flex"`,
`DEFAULT_OCPUS=2.0`, `DEFAULT_MEMORY_IN_GBS=8.0`, `DEFAULT_IMAGE_OS="Canonical
Ubuntu"`, `DEFAULT_IMAGE_OS_VERSION="24.04"`, VCN/subnet CIDRs
(`10.0.0.0/16`, `10.0.0.0/24`), resource names (`wisp-vcn`, `wisp-subnet`,
`wisp-security-list`, `wisp-route-table`, `wisp-internet-gateway`),
`DEFAULT_INSTANCE_NAME_PREFIX="wisp-instance"`, `DEFAULT_KEY_PAIR_NAME`, and
`DEFAULT_COMPARTMENT_ID=""` (defaults to the tenancy OCID).

### `pulumi.py` — the Pulumi program

Module-level `_plugins_ready` flag guards `ensure_plugins()`, which installs the
`oci` (`v4.22.0`) and `tls` (`v5.5.1`) plugins once.

- `get_ubuntu_image_id(compartment_id, region, ...)` — most recent Ubuntu image
  via the OCI SDK (`ComputeClient.list_images`).
- `get_default_username(image_os)` — maps OS to default SSH user (`ubuntu`,
  `opc`; fallback `ubuntu`).
- `create_vcn`, `create_internet_gateway`, `create_route_table`,
  `create_subnet`, `get_security_list` — network scaffolding for the instance.
- `create_compute_instance(...)` — Flex-shape Compute Instance with a public IP
  and the SSH public key in metadata.
- `create_oci_instance(region, compartment_id, force_current_ip=False, *, ...)`
  — the program passed to Pulumi. Wires everything together, generates an
  RSA 4096 `tls.PrivateKey` (`algorithm="RSA", rsa_bits=4096`), and exports:
  `instance_id`, `instance_public_ip`, `instance_private_ip`,
  `instance_private_key`, `wireguard_port`, `ssh_user`.

### `provider.py` — `OCIProvider(PulumiProvider)`

- `credentials` (property) — the resolved `OCICredentials`.
- `_get_compartment_id()` — compartment OCID, defaulting to the tenancy OCID
  (root compartment).
- `_create_pulumi_program(...)` — wraps `create_oci_instance`; treats
  `wireguard_port <= 0` as "random".
- `_get_oci_config()` — builds the OCI SDK config: explicit credentials when
  configured, otherwise falls back to `oci.config.from_file()` (reads
  `~/.oci/config` with the given profile); returns a minimal config on failure
  so validation fails with a clear error.
- `get_available_regions()` — subscribed regions via the OCI Identity API
  (`list_region_subscriptions`); raises `CredentialError` if credentials are
  missing or invalid.
- `_provider_name` — `"OCI"`.
- `deploy_vm(...)` / `delete_vm(...)` — shared flow, see
  [deployment flow](../deployment-flow.md).
