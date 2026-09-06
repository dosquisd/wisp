from src.wireguard.local import (
    configure_local_wireguard_client,
    connect_wireguard_client,
    disconnect_wireguard_client,
)
from src.wireguard.server import configure_remote_server

__all__ = [
    "configure_local_wireguard_client",
    "configure_remote_server",
    "connect_wireguard_client",
    "disconnect_wireguard_client",
]
