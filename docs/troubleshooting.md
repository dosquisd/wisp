# Troubleshooting

Field-tested fixes — most of these were hit, diagnosed, and resolved in real
sessions. When something fails, `--log-level debug` on any CLI command (or
`WISP_LOG_DIR/wisp.log`, e.g. `~/.local/state/wisp/log/wisp.log` on Linux)
usually names the exact step. Daemon-side issues are diagnosed with
`journalctl -u wisp.service` on Linux; on Windows the daemon logs to
`C:\ProgramData\wisp\logs\wisp.log`.

## Daemon and socket

### `PermissionError` when the CLI/TUI talks to the daemon

The Unix socket is group-restricted (`0660 root:wisp`). You must be a member
of the `wisp` group **and** the membership must be active in your login
session:

```bash
groups | grep wisp        # member?
sudo usermod -aG wisp $USER
newgrp wisp               # or log out and back in
```

### Daemon not running / not responding

```bash
systemctl status wisp.service       # is it active?
journalctl -u wisp.service -n 40    # why did it fail?
sudo systemctl restart wisp.socket wisp.service
```

On Windows: `Get-Service WispService` and the Windows Event Viewer.

### The daemon rejects the client config

The daemon rejects client configs containing `PreUp`/`PostUp`/`PreDown`/
`PostDown` — `wg-quick` would execute them as root, so the socket boundary
does not allow them. This is intentional; see [security.md](security.md).

## Deploys

### Pulumi fails with auth/lock errors

- Deployments need an authenticated Pulumi backend: `pulumi login` (the state
  lives on Pulumi Cloud by default). If you use local state with a passphrase,
  make sure `PULUMI_CONFIG_PASSPHRASE` is set.
- A crashed deploy can leave the stack locked: `wisp gc` shows it, and
  `pulumi cancel -s <stack>` clears the lock.

### The tunnel comes up but there is no internet

Work the layers in order — each one was a real failure during development:

1. **Handshake first** (client): `sudo wg show wg0` — if `latest handshake` is
   old or missing and `transfer: received` is 0 B, the UDP port is blocked.
   The cloud firewall/security list must allow **UDP on the WireGuard port**,
   and the instance firewall must let it through (on Oracle Linux OCI images,
   firewalld's default zone only allows SSH — open the port with
   `firewall-cmd --add-port=<port>/udp`). `sudo tcpdump -ni any 'udp port
   <port>'` on the server tells you whether the packets even arrive.
2. **Server forwarding**: `sudo sysctl net.ipv4.ip_forward` must be `1` (the
   installer sets it via `/etc/sysctl.d/wg.conf`).
3. **NAT**: the installer adds `MASQUERADE` rules for the server's default
   NIC — verify with `sudo iptables -t nat -S | grep MASQ`.

### Oracle Linux specifics

- The installer creates `/etc/wireguard/` with mode `0700` and files `0600` —
  an earlier `chmod 600 -R` (no execute on the directory) made `wg-quick`
  fail with "conf does not exist" even though the file was there.
- Re-running the installer with a stale `/etc/wireguard/params` triggers its
  interactive manage menu — Wisp's deploy pre-cleans that state for you.
- OL8 needs `oraclelinux-developer-release-el8` for `wireguard-tools`; OL9+
  ships it in the base repos.
- With firewalld running, `firewall-cmd` inside wg-quick's `PostUp` fails
  from a systemd unit (dbus denies the sender on EL9) — Wisp configures the
  zone at install time instead.

### "Deleting" a VPS session does not delete a VM

Correct — a Custom VPS is your server. The destroy tears the tunnel down on
both ends and removes Wisp's own configs; the machine, packages, and any
non-Wisp WireGuard config stay untouched.

## Leftovers and orphans

- On startup, Wisp warns about sessions left behind by dead processes and
  offers to clean them up.
- `wisp gc [--refresh] [--destroy]` inspects leftover Pulumi stacks directly
  from their state. With a local/file Pulumi backend, losing the machine
  loses the state — orphans become invisible until you find them in your
  provider console.
- After `gc --destroy`, the local SSH key and client conf of the destroyed
  sessions are removed too.

## Client-side oddities

- **Windows: script fails right after edits** — check for CRLF line endings
  if the `.sh`/`.conf` files were edited on Windows (`dos2unix`).
- **PowerShell quoting**: environment variables with `$` in the `wisp.toml`
  example values need single quotes.
- **Tunnel dies exactly one hour after deploy**: that is the TTL watchdog
  doing its job (`[general].max_session_ttl_minutes`, default 60). Use
  `--ttl 0` for long-lived debugging sessions.
