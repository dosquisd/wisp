# `wisp.cli`

The Textual terminal UI. For a task-oriented walkthrough see
[usage.md](../usage.md#the-tui); this is a module reference.

> The TUI's user-facing strings are in Spanish.

## `cli/app.py` — `WispApp(App)`

- Title "Wisp", subtitle "Ephemeral WireGuard VPNs on your own cloud".
- Global CSS (dark theme, cards, primary/secondary/danger buttons).
- Bindings: `q` / `Ctrl+C` → quit.
- Holds an `AppState` instance.
- `on_mount` installs and registers the `main_menu`, `config`, and `deploy`
  screens, then pushes `main_menu`.

## `cli/state.py` — `AppState`

Dataclass of in-memory session state, with TOML-derived defaults:

- `config: WispConfig` — built via `load_wisp_config()` (from the `[general]`
  TOML section).
- `provider_name: str` — from `get_default_provider()` (default `"aws"`).
- `selected_region: str` — default region for the default provider
  (`get_default_region_for(provider)`), falling back to `"us-east-2"`.
- `last_deployment: DeployVMResult | None`
- `aws_credentials: AWSCredentials` / `oci_credentials: OCICredentials` —
  resolved credentials.
- `get_credentials_for_provider(provider_name)` — returns the resolved
  credentials for `"aws"` or `"oci"`.
- `refresh_credentials()` — re-resolves credentials from TOML/env after config
  changes (calls `reload_toml_config()`).
- `reset_config()` — restores a fresh `WispConfig` from TOML.

## `cli/__main__.py`

Adds the repo root to `sys.path` and runs `WispApp()` — enables
`python -m wisp.cli`.

## `cli/screens/`

| Screen | Responsibility |
| -------- | ---------------- |
| `MainMenuScreen` | Banner, live config summary, navigation (`1` deploy, `2` config, `3` quit) |
| `ConfigScreen` | Edits `WispConfig` in memory with inline validation; Save / Reset / Back |
| `DeployScreen` | Provider (aws and oci today — see `ProviderEnum` ([`providers/base.py`](../../src/wisp/providers/base.py)) for the current list) + region selection; fetches live regions in a worker thread (fallback list on failure); pushes `ProgressScreen` |
| `ProgressScreen` | Runs `deploy_vm`/`delete_vm` in a worker thread, marshals progress to the UI via `call_from_thread`, shows results and a Destroy button |

### Threading note

Long-running provider calls run in Textual `@work(thread=True)` workers. UI
updates from those threads go through `self.app.call_from_thread(...)` to stay on
the UI thread.
