"""AWS provider implementation using shared Pulumi base."""

from collections.abc import Sequence

import boto3

from wisp.providers.aws.constants import DEFAULT_REGION
from wisp.providers.aws.pulumi import create_ec2_instance
from wisp.providers.pulumi_base import PulumiProvider


class AWSProvider(PulumiProvider):
    """AWS implementation using shared Pulumi deployment flow."""

    def _create_pulumi_program(
        self,
        region: str,
        force_current_ip: bool = False,
        wireguard_port: int | None = None,
    ) -> None:
        """Build the Pulumi program closure for AWS EC2 instance."""
        create_ec2_instance(
            region,
            force_current_ip=force_current_ip,
            wireguard_port=wireguard_port
            if (wireguard_port and wireguard_port > 0)
            else None,
        )

    def get_available_regions(self) -> Sequence[str]:
        """List enabled AWS regions via ``ec2.describe_regions`` (boto3)."""
        client = boto3.client("ec2", region_name=DEFAULT_REGION)
        return [r["RegionName"] for r in client.describe_regions()["Regions"]]

    @property
    def _provider_name(self) -> str:
        """Display name for progress messages."""
        return "AWS"
