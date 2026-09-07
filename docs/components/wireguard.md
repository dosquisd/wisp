# `wisp.wireguard`

Orchestrates the remote WireGuard server (via Ansible) and the local client (via
the daemon).

## `wireguard/remote_server.py`

### `configure_remote_server(inventory_context: InventoryContext) -> None`

1. Renders `templates/inventory.ini.j2` → `inventory/inventory.ini` using the
   provided `InventoryContext` (`utils.render_inventory_template`).
2. Resolves `ansible-playbook` (`utils.get_ansible_playbook_bin`).
3. Runs `ansible-playbook -i inventory/inventory.ini ansible/wireguard_install.yaml`
   with `check=True`.

The playbook installs and configures the WireGuard server on the VM and fetches
the generated client config back to `wireguard-confs/wg0-client.conf`. See
[deployment flow](../deployment-flow.md#deploy).

## `wireguard/local_client.py`

Thin client that talks to the privileged daemon over `/run/wisp.sock`.

- `_send(req: Request) -> Response` — connects to `SOCKET_PATH`, sends one
  request, reads one response line. Raises a descriptive `PermissionError` if the
  socket cannot be connected (typically missing `wisp` group membership).
- `connect_wireguard_client(config_content: str) -> Response` — `CONNECT` with
  the config body.
- `disconnect_wireguard_client() -> Response` — `DISCONNECT`.
- `status_wireguard_client() -> Response` — `STATUS`.

## `InventoryContext` (`wisp.schemas`)

`TypedDict` of the variables consumed by `templates/inventory.ini.j2`: SSH user,
instance IP, SSH key file, WireGuard port, allowed IPs, public IP, interface,
IPv4/IPv6, DNS 1/2, client name, client IPv4/IPv6, and `skip_client`.
