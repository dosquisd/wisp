"""OCI provider constants and defaults."""

DEFAULT_COMPARTMENT_ID: str = ""
DEFAULT_SHAPE: str = "VM.Standard.A1.Flex"
DEFAULT_OCPUS: float = 2.0
DEFAULT_MEMORY_IN_GBS: float = 8.0
DEFAULT_IMAGE_OS: str = "Canonical Ubuntu"
DEFAULT_IMAGE_OS_VERSION: str = "24.04"
DEFAULT_VCN_CIDR: str = "10.0.0.0/16"
DEFAULT_SUBNET_CIDR: str = "10.0.0.0/24"
DEFAULT_DNS_LABEL: str = "wispvcn"
DEFAULT_SUBNET_DNS_LABEL: str = "wispsubnet"
DEFAULT_SECURITY_LIST_NAME: str = "wisp-security-list"
DEFAULT_ROUTE_TABLE_NAME: str = "wisp-route-table"
DEFAULT_INTERNET_GATEWAY_NAME: str = "wisp-internet-gateway"
DEFAULT_VCN_NAME: str = "wisp-vcn"
DEFAULT_SUBNET_NAME: str = "wisp-subnet"
DEFAULT_INSTANCE_NAME_PREFIX: str = "wisp-instance"
DEFAULT_KEY_PAIR_NAME: str = "wisp-key-pair"
