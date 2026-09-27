"""GCP provider implementation using shared Pulumi base."""

from collections.abc import Sequence

from google.cloud import compute_v1

from wisp.config.credentials import (
    GCPCredentials,
    _load_google_credentials,
    resolve_gcp_credentials,
)
from wisp.providers.base import CredentialError, ProviderEnum
from wisp.providers.gcp.pulumi import create_gcp_instance
from wisp.providers.pulumi_base import PulumiProvider


class GCPProvider(PulumiProvider):
    """GCP implementation using shared Pulumi deployment flow."""

    def __init__(self, credentials: GCPCredentials | None = None) -> None:
        """Initialize the GCP provider with optional credentials."""
        self._credentials = credentials or resolve_gcp_credentials()

    @property
    def credentials(self) -> GCPCredentials:
        """Return the GCP credentials."""
        return self._credentials

    def _create_pulumi_program(
        self,
        region: str,
        force_current_ip: bool = False,
        wireguard_port: int | None = None,
    ) -> None:
        """Build the Pulumi program closure for GCP Compute Instance."""
        create_gcp_instance(
            region,
            force_current_ip=force_current_ip,
            project_id=self._credentials.project_id or None,
            credentials_path=self._credentials.credentials_path or None,
            zone=self._credentials.get_zone() or None,
            wireguard_port=wireguard_port
            if (wireguard_port and wireguard_port > 0)
            else None,
        )

    def get_available_regions(self) -> Sequence[str]:
        """List the project's GCP regions via the Compute SDK.

        Credentials are resolved explicitly via :func:`google.auth.default`
        (respecting ``credentials_path`` when set via service account file),
        rather than relying on implicit ADC.

        Raises:
            CredentialError: If GCP credentials are not configured or invalid.
        """
        if not self._credentials.project_id:
            raise CredentialError(
                "GCP project not configured. Set 'project_id' in the [gcp] "
                "section of wisp.toml, or run 'gcloud config set project "
                "<project-id>' to set up."
            )

        try:
            client = compute_v1.RegionsClient(
                credentials=_load_google_credentials(self._credentials)
            )
            request = compute_v1.ListRegionsRequest(
                project=self._credentials.project_id
            )
            response = client.list(request=request)
        except Exception as e:
            raise CredentialError(
                f"GCP credentials invalid: {e}. Check Application Default "
                "Credentials ('gcloud auth application-default login') or "
                "wisp.toml config."
            ) from e

        return [r.name for r in response]

    @property
    def _provider_name(self) -> str:
        """Display name for progress messages."""
        return ProviderEnum.GCP.value.upper()
