"""Local WireGuard client: thin wrapper that drives the privileged daemon.

Each function sends a single :class:`~wisp.daemon.protocol.Request` to the daemon
over the Unix socket and returns its :class:`~wisp.daemon.protocol.Response`.
"""

import socket

from wisp.daemon.protocol import SOCKET_PATH, ActionEnum, Request, Response


def _send(req: Request) -> Response:
    """Send one request to the daemon socket and read one response.

    Args:
        req (Request): The command to send.

    Returns:
        Response: The daemon's reply.

    Raises:
        PermissionError: If the socket cannot be connected — typically because
            the user is not yet in the ``wisp`` group (requires a re-login).
    """
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        try:
            sock.connect(SOCKET_PATH)
        except PermissionError as e:
            raise PermissionError(
                f"Cannot connect to the wisp daemon socket at {SOCKET_PATH}. "
                "You may need to log out and log back in for your 'wisp' group "
                "membership to take effect."
            ) from e

        sock.sendall(req.encode())
        raw = sock.makefile().readline().encode()
        return Response.decode(raw)


def connect_wireguard_client(config_content: str) -> Response:
    """Ask the daemon to write the config and bring ``wg0`` up.

    Args:
        config_content (str): The full WireGuard client configuration.
    """
    return _send(Request(action=ActionEnum.CONNECT, config_content=config_content))


def disconnect_wireguard_client() -> Response:
    """Ask the daemon to bring the ``wg0`` interface down."""
    return _send(Request(action=ActionEnum.DISCONNECT))


def status_wireguard_client() -> Response:
    """Ask the daemon for the current ``wg0`` status."""
    return _send(Request(action=ActionEnum.STATUS))
