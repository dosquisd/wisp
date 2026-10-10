# `wisp.cli`

The Textual terminal UI. For a task-oriented walkthrough see
[usage.md](../usage.md#the-tui); this is a module reference.

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
- `aws_credentials` / `oci_credentials` / `gcp_credentials` /
  `vps_credentials` — resolved credentials.
- `session_ttl_minutes: int | None` — per-deployment TTL override set by the
  deploy screen; `None` falls back to `config.max_session_ttl_minutes`.
- `effective_session_ttl()` — the TTL the deploy should schedule (0 = off).
- `get_credentials_for_provider(provider_name)` — returns the resolved
  credentials for the provider (`None` for unknown ones).
- `refresh_credentials()` — re-resolves credentials from TOML/env after config
  changes (calls `reload_toml_config()`).
- `reset_config()` — restores a fresh `WispConfig` from TOML.

## `cli/__main__.py`

Adds the repo root to `sys.path` and runs `WispApp()` — enables
`python -m wisp.cli`.

## `cli/screens/`

| Screen | Responsibility |
| -------- | ---------------- |
| `MainMenuScreen` | Banner, live config summary, orphan warning + cleanup entry, navigation (`1` deploy, `2` settings, `3` exit) |
| `ConfigScreen` | Edits `WispConfig` in memory with inline validation (including `max_session_ttl_minutes`); Save / Reset / Back |
| `DeployScreen` | Provider (`aws`, `oci`, `gcp`, `vps` — see `ProviderEnum` ([`providers/base.py`](../../src/wisp/providers/base.py)) for the current list) + region selection; fetches live regions in a worker thread (repopulates the standard list on failure and drops stale fetches from fast provider switching); swaps the region step for VPS connection fields when `vps` is selected; session TTL watchdog row; pushes `ProgressScreen` |
| `ProgressScreen` | Arms the session guard BEFORE provisioning starts; runs `deploy_vm`/`delete_vm` in a worker thread, marshals progress to the UI via `call_from_thread`, shows results and a Destroy button; on failure shows a scrollable box with the real Pulumi diagnostics (`_extract_error_details` unwraps `exc.command_result.stderr/stdout`) plus a Destroy Resources button |

### Threading note

Long-running provider calls run in Textual `@work(thread=True)` workers. UI
updates from those threads go through `self.app.call_from_thread(...)` to stay on
the UI thread.
