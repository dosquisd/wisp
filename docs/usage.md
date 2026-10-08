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

## CLI subcommands

Every subcommand accepts a positional `provider` argument (default `aws`;
`aws`, `oci`, and `gcp` today — see `ProviderEnum` for the current list).

> **Note:** Wisp ships with support for `aws`, `oci`, and `gcp` as of this writing, and
> the provider layer is extensible. For the current list, see `ProviderEnum`
> ([`src/wisp/providers/base.py`](../src/wisp/providers/base.py)) and
> `PROVIDERS_MAP`
> ([`src/wisp/providers/__init__.py`](../src/wisp/providers/__init__.py)).

### `wisp deploy [provider] [-r/--region REGION]`

Provisions a VM and brings the tunnel up.

- `provider` — cloud provider (`aws`, `oci`, or `gcp`, default `aws`).
- `-r`, `--region` — target region. If omitted, the region is resolved from
  the provider configuration in `wisp.toml` (`[aws].region` or `[oci].region`).
  There is no cross-provider default region.

**Examples:**

```bash
wisp deploy aws --region eu-west-1
wisp deploy oci            # uses the default region from [oci] in wisp.toml
wisp deploy aws -r sa-north-1
```

Prints the deployment result as JSON, e.g.:

```json
{
  "instance_id": "i-0123456789abcdef0",
  "public_ip": "203.0.113.10",
  "private_ip": "10.0.0.5",
  "wireguard_port": 51820
}
```

### `wisp destroy [provider] [-r/--region REGION]`

Disconnects the local client, destroys the Pulumi stack, and removes local
artifacts (inventory, key, client config). Prints the number of deleted
resources:

```bash
wisp destroy aws -r eu-west-1
# → Deleted VM. Count: 4

wisp destroy oci -r sa-bogota-1
# → Deleted VM. Count: 2
```

### `wisp regions [provider]`

Lists the regions available for the provider (AWS via `boto3` `describe_regions`
or OCI via the Identity API). Prints a JSON array.

```bash
wisp regions aws
wisp regions oci
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

> Note: the TUI's user-facing strings are currently in Spanish; all
> documentation and CLI arguments are in English.

## The TUI

The TUI is built with [Textual](https://textual.textualize.io/). Global styles
and screen registration live in `cli/app.py`; per-session state lives in
`cli/state.py` (`AppState`).

### Screens

| Screen | File | Purpose |
| ------ | ---- | ------ |
| Main menu | `screens/main_menu.py` | Entry point; shows current config summary; navigate to Deploy/Config/Quit |
| Configuration | `screens/config.py` | Edit per-session `WispConfig` (in memory) |
| Deploy | `screens/deploy.py` | Pick provider + region, review summary, start deploy |
| Progress | `screens/progress.py` | Live deploy/destroy progress; shows results; destroy button |

### Navigation and key bindings

- Main menu: `1` deploy, `2` config, `3` quit. `q` / `Ctrl+C` quit anywhere.
- All screens: the arrow keys navigate between widgets — `Up`/`Down` (or
  `Tab`) move forward/backward in DOM order, and `Left`/`Right` do the same,
  which is what most people try inside a horizontal button group. The
  confirmation modals inherit the same arrows, so `Up`/`Down` (and
  `Left`/`Right`) move between their buttons too. While an `Input` or `Select`
  is focused, its own arrow handling wins (text cursor / option list), so
  typing and picking are never hijacked.
- Config / Deploy / Progress: `Escape` goes back.

### Configuration screen

Edits an in-memory `WispConfig` for the session (persisted to the active
`wisp.toml` only when you press *Save*). Fields:

- `vm_boot_timeout` (seconds, minimum 5)
- `wireguard_port` (`0` = random in `49152–65535`, otherwise `0–65535`)
- `wireguard_interface` (non-empty)
- Primary / secondary DNS (both non-empty)
- Restrict access to your current public IP only (toggle → `/32` firewall rule)

Validation errors are shown inline. Both *Guardar* and *Restablecer* ask for
confirmation first: saving opens a "¿Guardar la configuración?" modal (the
form is validated before the modal appears), and resetting confirms before the
form is reloaded from `wisp.toml`.

Unsaved edits are tracked: a yellow "Hay cambios sin guardar" marker appears
as soon as a field differs from what was loaded. Leaving via `Escape`/*Volver*
or pressing *Restablecer* while there are unsaved edits opens the discard
modal — you can *Guardar* (persist and leave), *Descartar* (revert), or
*Cancelar* (stay and keep editing). Cancelling any confirmation modal never
loses edits: the dirty marker stays. The provider credential collapsibles are
read-only; the "Mostrar valores completos" toggle only reveals them.

### Deploy screen

- Provider select (`aws`, `oci`, or `gcp`).
- Region select. On mount, it fetches live regions in a background thread.
- A summary reflects the current config; "Start Deployment" pushes the
  Progress screen which runs the deployment in a worker thread.

The deploy card fits a 24-row terminal: there is deliberately no scroll, so
the *Iniciar Despliegue / Cancelar* buttons are always on screen.

### Progress screen

- Runs `deploy_vm` / `delete_vm` in a worker thread and marshals progress back
  to the UI thread via `call_from_thread`.
- The progress bar is centred above the status line. During the WireGuard
  install the remote installer's own output is streamed live into the status
  line (throttled to one line per second), so a minutes-long install never
  looks like a hang.
- On success, shows instance ID, public IP, WireGuard port, and private IP,
  plus a "Destroy VPN" button that runs the destroy flow.
- On error, shows the exception message.

### Tunnel screen

The tunnel view is a terminal state: `q`, `Ctrl+C`, `esc`, `d`, and the
*Destruir Túnel y Salir* button all tear the VPN down and exit — there is
deliberately no way back to the menu with a live session (a tunnel nobody
watches is a VM nobody tears down). Because that destroy is irreversible, a
*Confirmation* modal asks first unless `[general].confirm_destroy` is `false`
— `q` and `Ctrl+C` ask too when a tunnel is live, while on every other screen
they quit straight away. The dialog's "No volver a preguntar" checkbox turns
that off and persists it.
