"""GCP provider constants and defaults.

Provisioning model: SPOT (matching the ephemeral concept):
- ``on_host_maintenance = TERMINATE``
- ``instance_termination_action = DELETE`` (VMs are deleted, not stopped)
- ``automatic_restart = False``
"""

DEFAULT_GCP_VM_INSTANCE: str = "e2-micro"
DEFAULT_GCP_REGION: str = "us-central1"
DEFAULT_GCP_ZONE: str = "us-central1-a"  # Default zone for the region

# Network: the instance attaches to the default VPC network and gets an
# ephemeral external IP via its access config (no VCN/subnet scaffolding
# is created — unlike AWS/OCI).
DEFAULT_GCP_NETWORK: str = "default"

# Ubuntu LTS image, referenced by family (no per-region lookup needed —
# GCP image family references resolve across regions).
DEFAULT_IMAGE_PROJECT: str = "ubuntu-os-cloud"
DEFAULT_IMAGE_FAMILY: str = "ubuntu-2404-lts-amd64"

# Firewall: GCP has no per-instance security groups; ingress is opened via a
# VPC-level firewall rule targeting the instance by network tag.
DEFAULT_GCP_FIREWALL_NAME: str = "wisp-firewall"
DEFAULT_GCP_TARGET_TAG: str = "wisp"
