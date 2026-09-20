"""Per-provider credential resolution for cloud providers.

Consumes the global configuration loaded by
:func:`wisp.config.settings.load_toml_config` (which reads ``wisp.toml``) and
resolves credentials from (in priority order):
1. Explicit values in the global TOML config
2. Environment variables / Provider CLI/SDK default chains
"""

import configparser
from abc import ABC
from dataclasses import dataclass
from pathlib import Path

from wisp.config.constants import OCI_DEFAULT_COMPARTMENT_ID
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


def _read_aws_cli_files(profile: str) -> dict[str, str]:
    """Best-effort, network-free peek at ``~/.aws/{credentials,config}``.

    Mirrors what :func:`resolve_oci_credentials` already does via the OCI
    SDK's own config loader — AWS just doesn't ship an equivalent
    ``from_file()`` helper we can call the same way, so this reads the same
    two INI files the AWS CLI itself reads. Never touches the network (no
    STS calls, no instance-metadata lookups): this only tells us whether
    *something* is on disk, not whether it's actually valid.

    Args:
        profile: Profile name from ``wisp.toml``, or ``""`` for the
            AWS CLI's own "default" profile.

    Returns:
        dict[str, str]: Whichever of ``region``/``access_key_id``/
            ``secret_access_key``/``session_token`` it found. Empty if the
            files don't exist or don't have that profile.
    """
    creds_section = profile or "default"
    config_section = f"profile {profile}" if profile else "default"
    found: dict[str, str] = {}

    creds_path = Path.home() / ".aws" / "credentials"
    if creds_path.is_file():
        parser = configparser.ConfigParser()
        try:
            parser.read(creds_path)
        except configparser.Error:
            parser = None
        if parser is not None and parser.has_section(creds_section):
            section = parser[creds_section]
            for toml_key, ini_key in (
                ("access_key_id", "aws_access_key_id"),
                ("secret_access_key", "aws_secret_access_key"),
                ("session_token", "aws_session_token"),
            ):
                if section.get(ini_key):
                    found[toml_key] = section[ini_key]

    config_path = Path.home() / ".aws" / "config"
    if config_path.is_file():
        parser = configparser.ConfigParser()
        try:
            parser.read(config_path)
        except configparser.Error:
            parser = None
        if parser is not None and parser.has_section(config_section):
            region = parser[config_section].get("region")
            if region:
                found["region"] = region

    return found


def resolve_aws_credentials() -> AWSCredentials:
    """Resolve AWS credentials from TOML config + the AWS CLI's own files.

    Values set in ``wisp.toml`` take priority; anything not set there falls
    back to whatever ``~/.aws/credentials`` / ``~/.aws/config`` already have
    for that profile (this is what previously only happened for OCI —
    without it, a perfectly normal ``aws configure`` setup showed up as
    "no configurado" in the TUI even though deploys worked fine, because
    boto3 was finding those files on its own, just later and separately).

    Note there's no hardcoded region fallback here (unlike before): an
    empty ``region`` is left empty so boto3 keeps resolving it itself
    (profile → env var → its own default) instead of Wisp silently forcing
    a region the person never asked for.
    """
    toml_config = load_toml_config()
    aws_toml = toml_config.get("aws", {})
    profile = aws_toml.get("profile", "")

    cli_config = _read_aws_cli_files(profile)

    return AWSCredentials(
        region=aws_toml.get("region", cli_config.get("region", "")),
        profile=profile,
        access_key_id=aws_toml.get(
            "access_key_id", cli_config.get("access_key_id", "")
        ),
        secret_access_key=aws_toml.get(
            "secret_access_key", cli_config.get("secret_access_key", "")
        ),
        session_token=aws_toml.get(
            "session_token", cli_config.get("session_token", "")
        ),
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
