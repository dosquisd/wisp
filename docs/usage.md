# Usage

Wisp has two modes: an interactive TUI (default) and non-interactive CLI
subcommands. Both are dispatched from `wisp.main:main` (`parse_args` + `main`).

## Launching

```bash
wisp            # no subcommand → launches the TUI
wisp deploy     # CLI: deploy a VM
wisp destroy    # CLI: destroy VMs
wisp regions    # CLI: list available regions
```

You can also launch the TUI directly with `python -m wisp.cli`.

## CLI subcommands

Every subcommand accepts a positional `provider` argument (default `aws`, the
only currently supported value).

### `wisp deploy [provider] [-r/--region REGION]`

Provisions a VM and brings the tunnel up.

- `provider` — cloud provider (default `aws`).
- `-r`, `--region` — target region (default `us-east-2`).

Prints the deployment result as JSON, e.g.:

```json
{
  "instance_id": "i-0123456789abcdef0",
  "public_ip": "203.0.113.10",
  "private_ip": "10.0.0.5",
  "wireguard_port": 51820
}
```

Example:

```bash
wisp deploy aws --region eu-west-1
```

### `wisp destroy [provider] [-r/--region REGION]`

Disconnects the local client, destroys the Pulumi stack, and removes local
artifacts (inventory, key, client config). Prints the number of deleted
resources:

```bash
wisp destroy aws -r eu-west-1
# → Deleted VM. Count: 4
```

### `wisp regions [provider]`

Lists the regions available for the provider (AWS: via
`boto3` `describe_regions`). Prints a JSON array.

```bash
wisp regions aws
```

## CLI vs TUI behaviour

- **TUI mode** (no subcommand): `WispApp().run()` is started and the process
  exits when the TUI closes. Deploy progress is shown live via the
  `on_progress` callback and a progress bar.
- **CLI mode**: the console log handler is raised to `DEBUG` so you see detailed
  logs on stderr, and the boot wait is shown with a `tqdm` progress bar. Results
  are printed as JSON / plain text and the process exits with code `0`.

Argument parsing normalizes `command`, `provider`, and `region` to lowercase. If
no command is given, it defaults to the TUI.

## The TUI

The TUI is built with [Textual](https://textual.textualize.io/). Global styles
and screen registration live in `cli/app.py`; per-session state lives in
`cli/state.py` (`AppState`).

> Note: the TUI's user-facing strings are currently in Spanish.

### Screens

| Screen | File | Purpose |
|--------|------|---------|
| Main menu | `screens/main_menu.py` | Entry point; shows current config summary; navigate to Deploy/Config/Quit |
| Configuration | `screens/config.py` | Edit per-session `WispConfig` (in memory) |
| Deploy | `screens/deploy.py` | Pick provider + region, review summary, start deploy |
| Progress | `screens/progress.py` | Live deploy/destroy progress; shows results; destroy button |

### Navigation and key bindings

- Main menu: `1` deploy, `2` config, `3` quit. `q` / `Ctrl+C` quit anywhere.
- Config / Deploy / Progress: `Escape` goes back.

### Configuration screen

Edits an in-memory `WispConfig` for the session (not persisted to disk). Fields:

- Ansible timeout (seconds, minimum 5)
- WireGuard port (`0` = random in `49152–65535`, otherwise `0–65535`)
- WireGuard interface (non-empty)
- Primary / secondary DNS (both non-empty)
- Restrict access to your current public IP only (toggle → `/32` firewall rule)

Validation errors are shown inline. "Save" stores to the in-memory `AppState`;
"Reset" restores defaults.

### Deploy screen

- Provider select (AWS only).
- Region select. On mount, it fetches live AWS regions in a background thread
  (`boto3`); if that fails it falls back to a built-in region list.
- A summary reflects the current config; "Iniciar Despliegue" pushes the
  Progress screen which runs the deployment in a worker thread.

### Progress screen

- Runs `deploy_vm` / `delete_vm` in a worker thread and marshals progress back to
  the UI thread via `call_from_thread`.
- On success, shows instance ID, public IP, WireGuard port, and private IP, plus
  a "Destruir VPN" button that runs the destroy flow.
- On error, shows the exception message.
