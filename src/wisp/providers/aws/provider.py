"""AWS provider implementation using shared Pulumi base."""

from collections.abc import Sequence

import boto3

from wisp.config.credentials import (
    AWSCredentials,
    resolve_aws_credentials,
    validate_aws_credentials,
)
from wisp.providers.aws.pulumi import create_ec2_instance
from wisp.providers.base import CredentialError, ProviderEnum
from wisp.providers.pulumi_base import PulumiProvider


class AWSProvider(PulumiProvider):
    """AWS implementation using shared Pulumi deployment flow."""

    def __init__(self, credentials: AWSCredentials | None = None) -> None:
        """Initialize the AWS provider with optional credentials."""
        self._credentials = credentials or resolve_aws_credentials()

    @property
    def credentials(self) -> AWSCredentials:
        """Return the AWS credentials."""
        return self._credentials

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
        """List enabled AWS regions via ``ec2.describe_regions`` (boto3).

        Raises:
            CredentialError: If AWS credentials are not configured or invalid.
        """
        if not validate_aws_credentials(self._credentials):
            raise CredentialError(
                "AWS credentials not configured. Set via TOML, environment variables, "
                "or ~/.aws/credentials. Run 'aws configure' to set up."
            )

        client = boto3.client("ec2", **self._credentials.to_boto3_params())
        return [r["RegionName"] for r in client.describe_regions()["Regions"]]

    @property
    def _provider_name(self) -> str:
        """Display name for progress messages."""
        return ProviderEnum.AWS.value.upper()
