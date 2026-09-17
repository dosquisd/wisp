"""OCI provider implementation using shared Pulumi base."""

from collections.abc import Sequence

import oci
from oci.config import from_file as oci_config_from_file

from wisp.config.credentials import OCICredentials, resolve_oci_credentials
from wisp.providers.base import CredentialError, ProviderEnum
from wisp.providers.oci.pulumi import create_oci_instance
from wisp.providers.pulumi_base import PulumiProvider


class OCIProvider(PulumiProvider):
    """OCI implementation using shared Pulumi deployment flow."""

    def __init__(self, credentials: OCICredentials | None = None) -> None:
        """Initialize the OCI provider with optional credentials."""
        self._credentials = credentials or resolve_oci_credentials()

    @property
    def credentials(self) -> OCICredentials:
        """Return the OCI credentials."""
        return self._credentials

    def _get_compartment_id(self) -> str:
        """Get the compartment OCID (defaults to tenancy OCID for root compartment)."""
        return self._credentials.get_compartment_ocid()

    def _create_pulumi_program(
        self,
        region: str,
        force_current_ip: bool = False,
        wireguard_port: int | None = None,
    ) -> None:
        """Build the Pulumi program closure for OCI Compute Instance."""
        compartment_id = self._get_compartment_id()
        create_oci_instance(
            region,
            compartment_id,
            force_current_ip=force_current_ip,
            wireguard_port=wireguard_port
            if (wireguard_port and wireguard_port > 0)
            else None,
        )

    def _get_oci_config(self) -> dict[str, str]:
        """Build OCI SDK config from credentials, using profile file if available.

        If credentials are explicitly configured, use them directly.
        Otherwise, fall back to oci.config.from_file() which reads ~/.oci/config
        with the specified profile.
        """
        if self._credentials.is_explicitly_configured():
            config = self._credentials.to_oci_config()
            if self._credentials.profile and self._credentials.profile != "DEFAULT":
                config["profile"] = self._credentials.profile
            return config

        # Fall back to OCI config file with profile
        try:
            return oci_config_from_file(profile_name=self._credentials.profile)
        except Exception:
            # If config file doesn't exist or profile not found, return minimal config
            # This will cause validation to fail later with a clear error
            return {}

    def get_available_regions(self) -> Sequence[str]:
        """List subscribed OCI regions via OCI Identity API.

        Raises:
            CredentialError: If OCI credentials are not configured or invalid.
        """
        config = self._get_oci_config()

        if not config or "tenancy" not in config:
            raise CredentialError(
                "OCI credentials not configured. Set via TOML, environment variables, "
                "or ~/.oci/config. Run 'oci setup config' to set up."
            )

        # Validate by actually calling the API
        try:
            identity_client = oci.identity.IdentityClient(config)
            identity_client.list_region_subscriptions(tenancy_id=config["tenancy"])
        except Exception as e:
            raise CredentialError(
                f"OCI credentials invalid: {e}. Check ~/.oci/config or TOML config."
            ) from e

        response = identity_client.list_region_subscriptions(
            tenancy_id=config["tenancy"]
        )
        return [r.region_name for r in response.data]

    @property
    def _provider_name(self) -> str:
        """Display name for progress messages."""
        return ProviderEnum.OCI.value.upper()
