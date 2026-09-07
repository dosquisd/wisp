# `wisp.providers`

Cloud provider abstraction and the AWS implementation.

## `providers/__init__.py`

- `ProviderEnum(enum.Enum)`: currently just `AWS = "aws"`.
- `PROVIDERS_MAP: dict[ProviderEnum, type[BaseProvider]]`: maps the enum to the
  concrete provider class (`{ProviderEnum.AWS: AWSProvider}`).

## `providers/base.py` — `BaseProvider` (ABC)

Result/callback types:

- `ProgressCallback = Callable[[str, float | None], None]`
- `DeployVMResult(TypedDict)`: `instance_id`, `public_ip`, `private_ip`,
  `wireguard_port`.

Abstract methods:

| Method | Returns | Purpose |
|--------|---------|---------|
| `get_available_regions()` | `Sequence[str]` | List provider regions |
| `deploy_vm(region, force_current_ip=False, config=None, on_progress=None)` | `DeployVMResult` | Provision + configure + connect |
| `delete_vm(region, on_progress=None)` | `int` | Disconnect + destroy + cleanup, returns deleted count |

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
  passed to Pulumi. Creates the SG, an ED25519 `tls.PrivateKey`, an
  `aws.ec2.KeyPair` from its OpenSSH public key, and the `aws.ec2.Instance`.
  Exports: `instance_id`, `instance_public_ip`, `instance_private_ip`,
  `instance_private_key`, `wireguard_port`, `ssh_user`.

### `provider.py` — `AWSProvider(BaseProvider)`

- `__create_pulumi_program(region, force_current_ip=False, wireguard_port=None)`
  — wraps `create_ec2_instance`; treats `wireguard_port <= 0` as "random".
- `get_available_regions()` — `boto3` `ec2.describe_regions()` (queried from
  `DEFAULT_REGION`).
- `deploy_vm(...)` — see [deployment flow](../deployment-flow.md#deploy).
- `delete_vm(...)` — see [deployment flow](../deployment-flow.md#destroy).
