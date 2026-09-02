import uuid

import pulumi
import pulumi_aws as aws
import pulumi_tls as tls
from pulumi import automation as auto

from src.config.constants import DEFAULT_TAG
from src.providers.aws.constants import (
    DEFAULT_AMI_NAME,
    DEFAULT_AMI_OWNER,
    DEFAULT_EC2_INSTANCE_TYPE,
)
from src.utils import get_public_ip, get_wireguard_port, logger

# Just in case we need to ensure that the AWS plugin is installed for Pulumi automation
_plugins_ready = False


def ensure_plugins() -> None:
    global _plugins_ready
    if _plugins_ready:
        return
    auto.LocalWorkspace().install_plugin("aws", "v7.44.0")
    auto.LocalWorkspace().install_plugin("tls", "v5.5.1")
    _plugins_ready = True


def get_ami(
    region: str | None = None,
    *,
    owners: list[str] | None = None,
    ami_names: list[str] | None = None,
) -> aws.ec2.GetAmiResult:
    if owners is None:
        owners = [DEFAULT_AMI_OWNER]

    if ami_names is None:
        ami_names = [DEFAULT_AMI_NAME]

    ami = aws.ec2.get_ami(
        most_recent=True,
        owners=owners,
        filters=[aws.ec2.GetAmiFilterArgs(name="name", values=ami_names)],
        region=region,
    )

    return ami


def get_default_username(ami_name: str) -> str:
    ami_lower = ami_name.lower()
    if "ubuntu" in ami_lower:
        return "ubuntu"
    elif "amzn" in ami_lower or "amazon-linux" in ami_lower:
        return "ec2-user"
    elif "centos" in ami_lower:
        return "centos"
    elif "debian" in ami_lower:
        return "admin"
    return "ec2-user"


def get_security_group(
    region: str | None = None,
    force_current_ip: bool = False,
    *,
    name: str | None = None,
    description: str | None = None,
    wireguard_port: int | None = None,
    cidr_blocks: list[str] | None = None,
) -> aws.ec2.SecurityGroup:
    if name is None:
        name = "wisp-sg"
        logger.debug(f"No security group name provided, using default '{name}'")

    if description is None:
        description = "Security group for WISP - WireGuard VPN"
        logger.debug(
            f"No security group description provided, using default '{description}'"
        )

    if wireguard_port is None:
        wireguard_port = get_wireguard_port()
        logger.debug(f"No WireGuard port provided, using default '{wireguard_port}'")

    if cidr_blocks is None:
        if force_current_ip:
            cidr_blocks = [f"{get_public_ip()}/32"]
        else:
            cidr_blocks = ["0.0.0.0/0"]

        logger.debug(f"No CIDR blocks provided, using default '{cidr_blocks}'")

    return aws.ec2.SecurityGroup(
        name,
        description=description,
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                protocol="udp",
                from_port=0,
                to_port=wireguard_port,
                cidr_blocks=cidr_blocks,
            ),
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=0,
                to_port=22,
                cidr_blocks=cidr_blocks,
            ),
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"]
            )
        ],
        region=region,
        tags=DEFAULT_TAG,
    )


def create_ec2_instance(
    region: str,
    /,
    force_current_ip: bool = False,
    *,
    # EC2 related
    custom_resource_name: str | None = None,
    instance_type: str = DEFAULT_EC2_INSTANCE_TYPE,
    # AMI related
    ami_owners: list[str] | None = None,
    ami_names: list[str] | None = None,
    # Security group related
    security_group_name: str | None = None,
    security_group_description: str | None = None,
    wireguard_port: int | None = None,
    cidr_blocks: list[str] | None = None,
) -> None:
    ensure_plugins()
    if custom_resource_name is None:
        custom_resource_name = f"wisp-instance-{uuid.uuid4().hex[:8]}"
        logger.debug(
            f"No custom resource name provided, using default '{custom_resource_name}'"
        )

    if wireguard_port is None:
        wireguard_port = get_wireguard_port()
        logger.debug(f"No WireGuard port provided, using default '{wireguard_port}'")

    logger.debug(
        f"Creating EC2 instance in region '{region}' with type '{instance_type}'"
    )

    ami = get_ami(region, owners=ami_owners, ami_names=ami_names)

    logger.debug(
        f"Creating security group '{security_group_name}' with description "
        f"'{security_group_description}' and WireGuard port '{wireguard_port}'"
    )
    security_group = get_security_group(
        region,
        force_current_ip,
        name=security_group_name,
        description=security_group_description,
        wireguard_port=wireguard_port,
        cidr_blocks=cidr_blocks,
    )

    # Generate a new WireGuard private key and create a corresponding AWS EC2 Key Pair
    logger.debug("Generating WireGuard private key and creating AWS EC2 Key Pair")

    tls_private_key = tls.PrivateKey(
        "wireguard-private-key",
        algorithm="ED25519",
        rsa_bits=4096,
    )

    key_pair = aws.ec2.KeyPair(
        "wireguard-key-pair",
        public_key=tls_private_key.public_key_openssh,
        region=region,
        tags=DEFAULT_TAG,
    )

    # Create the EC2 instance with the specified parameters
    instance = aws.ec2.Instance(
        custom_resource_name,
        instance_type=instance_type,
        ami=ami.id,
        tags={"Name": custom_resource_name, **DEFAULT_TAG},
        region=region,
        vpc_security_group_ids=[security_group.id],
        key_name=key_pair.key_name,
    )

    pulumi.export("instance_id", instance.id)
    pulumi.export("instance_public_ip", instance.public_ip)
    pulumi.export("instance_private_ip", instance.private_ip)
    pulumi.export("instance_private_key", tls_private_key.private_key_pem)
    pulumi.export("wireguard_port", wireguard_port)
    pulumi.export("ssh_user", get_default_username(ami.name))
