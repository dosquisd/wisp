"""Per-provider credential resolution for cloud providers.

Consumes the global configuration loaded by
:func:`wisp.config.settings.load_toml_config` (which reads ``wisp.toml``) and
resolves credentials from (in priority order):
1. Explicit values in the global TOML config
2. Environment variables / Provider CLI/SDK default chains
"""

from abc import ABC
from dataclasses import dataclass

from wisp.config.constants import AWS_DEFAULT_REGION, OCI_DEFAULT_COMPARTMENT_ID
from wisp.config.settings import load_toml_config


class BaseCredentials(ABC):
    """Base class for provider credentials."""

    region: str = ""

    def is_explicitly_configured(self) -> bool:
        """Return True if any field is explicitly set (not relying on default chain)."""
        raise NotImplementedError("Subclasses must implement this method.")


# ─── AWS Credentials ─────────────────────────────────────────────


@dataclass
class AWSCredentials(BaseCredentials):
    """AWS authentication credentials.

    All fields optional — if not set, boto3 default credential chain is used
    (env vars, ~/.aws/credentials, ~/.aws/config, IAM roles).
    """

    region: str = ""
    profile: str = ""
    access_key_id: str = ""
    secret_access_key: str = ""
    session_token: str = ""

    def is_explicitly_configured(self) -> bool:
        """True if any field is explicitly set (not relying on default chain)."""
        return any(
            [
                self.region,
                self.profile,
                self.access_key_id,
                self.secret_access_key,
                self.session_token,
            ]
        )

    def to_boto3_params(self) -> dict[str, str]:
        """Convert to boto3 client/session parameters (excludes empty values)."""
        params = {}
        if self.region:
            params["region_name"] = self.region
        if self.profile:
            params["profile_name"] = self.profile
        if self.access_key_id:
            params["aws_access_key_id"] = self.access_key_id
        if self.secret_access_key:
            params["aws_secret_access_key"] = self.secret_access_key
        if self.session_token:
            params["aws_session_token"] = self.session_token
        return params


# ─── OCI Credentials ─────────────────────────────────────────────


@dataclass
class OCICredentials(BaseCredentials):
    """OCI authentication credentials.

    All fields optional — if not set, OCI SDK default chain is used
    (~/.oci/config, env vars OCI_TENANCY/OCI_USER/OCI_FINGERPRINT/
    OCI_PRIVATE_KEY_PATH/OCI_REGION).
    """

    tenancy_ocid: str = ""
    user_ocid: str = ""
    fingerprint: str = ""
    private_key_path: str = ""
    region: str = ""
    compartment_ocid: str = ""
    profile: str = "DEFAULT"

    def is_explicitly_configured(self) -> bool:
        """True if any field is explicitly set."""
        return any(
            [
                self.tenancy_ocid,
                self.user_ocid,
                self.fingerprint,
                self.private_key_path,
                self.region,
                self.compartment_ocid,
                self.profile != "DEFAULT",
            ]
        )

    def get_compartment_ocid(self) -> str:
        """Return compartment OCID, defaulting to tenancy OCID (root)."""
        return self.compartment_ocid or self.tenancy_ocid

    def to_oci_config(self) -> dict[str, str]:
        """Convert to OCI SDK config dict (excludes empty values)."""
        config = {}
        if self.tenancy_ocid:
            config["tenancy"] = self.tenancy_ocid
        if self.user_ocid:
            config["user"] = self.user_ocid
        if self.fingerprint:
            config["fingerprint"] = self.fingerprint
        if self.private_key_path:
            config["key_file"] = self.private_key_path
        if self.region:
            config["region"] = self.region
        if self.profile != "DEFAULT":
            config["profile"] = self.profile
        return config


# ─── Resolution Functions ────────────────────────────────────────tions ────────────────────────────────────────


def resolve_aws_credentials() -> AWSCredentials:
    """Resolve AWS credentials from TOML config + SDK defaults.

    Values set in ``wisp.toml`` take priority; anything not set falls back to
    boto3's default credential chain (env vars, ~/.aws/credentials, IAM roles).
    """
    toml_config = load_toml_config()
    aws_toml = toml_config.get("aws", {})

    return AWSCredentials(
        region=aws_toml.get("region", AWS_DEFAULT_REGION),
        profile=aws_toml.get("profile", ""),
        access_key_id=aws_toml.get("access_key_id", ""),
        secret_access_key=aws_toml.get("secret_access_key", ""),
        session_token=aws_toml.get("session_token", ""),
    )


def resolve_oci_credentials() -> OCICredentials:
    """Resolve OCI credentials from TOML config + ~/.oci/config + environment.

    Values set in ``wisp.toml`` take priority; anything not set falls back to
    the OCI SDK default config chain (~/.oci/config, env vars).
    """
    toml_config = load_toml_config()
    oci_toml = toml_config.get("oci", {})

    # Try to load from OCI config file as fallback
    oci_config = {}
    try:
        import oci as oci_sdk

        oci_config = oci_sdk.config.from_file(
            profile_name=oci_toml.get("profile", "DEFAULT")
        )
    except Exception:
        pass  # Config file not found or invalid, use empty defaults

    return OCICredentials(
        tenancy_ocid=oci_toml.get("tenancy_ocid", oci_config.get("tenancy", "")),
        user_ocid=oci_toml.get("user_ocid", oci_config.get("user", "")),
        fingerprint=oci_toml.get("fingerprint", oci_config.get("fingerprint", "")),
        private_key_path=oci_toml.get(
            "private_key_path", oci_config.get("key_file", "")
        ),
        region=oci_toml.get("region", oci_config.get("region", "")),
        compartment_ocid=oci_toml.get("compartment_ocid", OCI_DEFAULT_COMPARTMENT_ID),
        profile=oci_toml.get("profile", "DEFAULT"),
    )


# ─── Validation Functions ────────────────────────────────────────


def validate_aws_credentials(creds: AWSCredentials) -> bool:
    """Validate AWS credentials by calling STS GetCallerIdentity.

    Returns True if credentials work, False otherwise.
    Uses boto3 with resolved credentials (or default chain if empty).
    """
    try:
        import boto3

        client = boto3.client("sts", **creds.to_boto3_params())
        client.get_caller_identity()
        return True
    except Exception:
        return False


def validate_oci_credentials(creds: OCICredentials) -> bool:
    """Validate OCI credentials by calling Identity list_region_subscriptions.

    Returns True if credentials work, False otherwise.
    """
    try:
        import oci

        config = creds.to_oci_config()
        if not config:
            return False  # No explicit creds to validate
        identity_client = oci.identity.IdentityClient(config)
        identity_client.list_region_subscriptions(tenancy_id=config["tenancy"])
        return True
    except Exception:
        return False
