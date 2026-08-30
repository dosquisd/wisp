import pulumi
import pulumi_aws as aws
from pulumi import automation as auto

from src.config.constants import CREATED_BY_TAG
from src.providers.aws.constants import (
    DEFAULT_AMI_NAME,
    DEFAULT_AMI_OWNER,
    DEFAULT_EC2_INSTANCE_TYPE,
)
from src.utils import get_public_ip, get_random_generator, get_wireguard_port

RANDOM_GENERATOR = get_random_generator()


# Just in case we need to ensure that the AWS plugin is installed for Pulumi automation
_plugins_ready = False


def ensure_plugins() -> None:
    global _plugins_ready
    if _plugins_ready:
        return
    auto.LocalWorkspace().install_plugin("aws", "v7.44.0")
    _plugins_ready = True


ensure_plugins()


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


def get_security_group(
    region: str | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    wireguard_port: int | None = None,
    cidr_blocks: list[str] | None = None,
) -> aws.ec2.SecurityGroup:
    if name is None:
        name = "wisp-sg"

    if description is None:
        description = "Security group for WISP - WireGuard VPN"

    if wireguard_port is None:
        wireguard_port = get_wireguard_port()

    if cidr_blocks is None:
        cidr_blocks = [f"{get_public_ip()}/32"]

    return aws.ec2.SecurityGroup(
        name,
        description=description,
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                protocol="udp",
                from_port=wireguard_port,
                to_port=wireguard_port,
                cidr_blocks=cidr_blocks,
            )
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"]
            )
        ],
        region=region,
        tags={
            "created-by": CREATED_BY_TAG,
        },
    )


def create_ec2_instance(
    region: str,
    /,
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
    if custom_resource_name is None:
        custom_resource_name = "wisp-instance"

    ami = get_ami(region, owners=ami_owners, ami_names=ami_names)

    security_group = get_security_group(
        region,
        name=security_group_name,
        description=security_group_description,
        wireguard_port=wireguard_port,
        cidr_blocks=cidr_blocks,
    )

    instance = aws.ec2.Instance(
        custom_resource_name,
        instance_type=instance_type,
        ami=ami.id,
        tags={
            "name": custom_resource_name,
            "created-by": CREATED_BY_TAG,
        },
        region=region,
        vpc_security_group_ids=[security_group.id],
    )

    pulumi.export("instance_id", instance.id)
    pulumi.export("instance_public_ip", instance.public_ip)
    pulumi.export("instance_private_ip", instance.private_ip)


def install_wireguard_on_ec2(instance_id: str) -> None:
    # Implement the logic to install WireGuard on an EC2 instance using Pulumi
    pass
