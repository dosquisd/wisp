import enum
import json
from dataclasses import asdict, dataclass

SOCKET_PATH = "/run/wisp.sock"

class ActionEnum(enum.StrEnum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    STATUS = "status"


@dataclass
class Request:
    action: ActionEnum
    config_content: str | None = None  # just for "connect" action, otherwise None

    def encode(self) -> bytes:
        return (json.dumps(asdict(self)) + "\n").encode()

    @staticmethod
    def decode(raw: bytes) -> "Request":
        return Request(**json.loads(raw.decode()))


@dataclass
class Response:
    ok: bool
    message: str = ""

    def encode(self) -> bytes:
        return (json.dumps(asdict(self)) + "\n").encode()

    @staticmethod
    def decode(raw: bytes) -> "Response":
        return Response(**json.loads(raw.decode()))
