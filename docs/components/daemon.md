# `wisp.daemon`

The privileged local daemon that controls the client-side WireGuard interface.
Runs as root under systemd; the unprivileged frontend talks to it over a Unix
socket. See also [security model](../security.md).

## `daemon/protocol.py`

- `SOCKET_PATH = "/run/wisp.sock"`.
- `ActionEnum(StrEnum)`: `CONNECT`, `DISCONNECT`, `STATUS`.
- `Request` dataclass: `action: ActionEnum`, `config_content: str | None`
  (only for `connect`). `encode()`/`decode()` use newline-terminated JSON.
- `Response` dataclass: `ok: bool`, `message: str`, with matching
  `encode()`/`decode()`.

## `daemon/server.py`

`WG_CONF_PATH = /etc/wireguard/wg0.conf`.

Handlers (async):

- `handle_connect(config_content)` — writes `WG_CONF_PATH` (`0600`), runs
  `wg-quick up wg0`. Returns `Response(ok=True, "connected")` or the command's
  stderr on `CalledProcessError`.
- `handle_disconnect()` — runs `wg-quick down wg0`.
- `handle_status()` — runs `wg show wg0`, returns stdout.
- `handle_client(reader, writer)` — reads one `Request`, dispatches by action,
  writes one `Response`. Unknown actions and exceptions yield `ok=False`.

`main()` starts an asyncio Unix-socket server. If `LISTEN_FDS` is set (systemd
socket activation) it adopts fd 3 (`_socket_from_systemd`); otherwise it binds
`SOCKET_PATH` directly (local development).

Run standalone with:

```bash
python -m wisp.daemon.server
```

(under systemd this is `wisp.service`, requiring `wisp.socket`).
