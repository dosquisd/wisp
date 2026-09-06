import socket

from src.daemon.protocol import SOCKET_PATH, ActionEnum, Request, Response


def _send(req: Request) -> Response:
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
    return _send(Request(action=ActionEnum.CONNECT, config_content=config_content))


def disconnect_wireguard_client() -> Response:
    return _send(Request(action=ActionEnum.DISCONNECT))


def status_wireguard_client() -> Response:
    return _send(Request(action=ActionEnum.STATUS))
