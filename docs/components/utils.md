# `wisp.utils`

Shared helpers. `utils/__init__.py` re-exports the common ones and uses module
`__getattr__` for lazy imports of the heavier Pulumi helpers.

## Exports

`get_public_ip`, `get_random_generator`, `get_wireguard_port`, `logger`,
`PlatformEnum`, `secure_file`. Lazily via `__getattr__`:
`create_or_select_pulumi_stack`.

## `utils/__init__.py`

- `get_public_ip() -> str` — GETs `https://api.ipify.org`.
- `__getattr__(name)` — lazy-imports `create_or_select_pulumi_stack` on first
  access; raises `AttributeError` otherwise.

## `utils/pulumi.py`

- `create_or_select_pulumi_stack(program=None, *, provider="aws", project_name=PULUMI_PROJECT_NAME) -> auto.Stack`
  — wraps `pulumi.automation.create_or_select_stack` with a provider-specific
  stack name via `get_pulumi_stack_name(provider)` (e.g. `wisp-stack-aws`,
  `wisp-stack-oci`).
- `list_wisp_stacks() -> list[str]` — every `wisp-stack-*` stack in the
  current backend (no program run).
- `stack_resource_counts(stack_name) -> dict[str, int]` — counts real
  resources (everything except the synthetic `pulumi:pulumi:Stack` root) from
  the stack's exported state; safe against broken credentials or drifted
  programs.
- `refresh_wisp_stack(program, *, provider, region) -> bool` — reconciles a
  stack's state against the cloud (`stack.refresh()`); never raises, returns
  `False` on failure.
- `destroy_wisp_stack(program, *, provider, region) -> int` — destroys a
  stack through the normal provider flow; returns the deleted-resource count.

> **Cycle note:** this module must NOT import `wisp.providers` at module
> level — the provider modules import `create_or_select_pulumi_stack` from
> `wisp.utils` (lazily via `utils/__init__.__getattr__`), which would close
> an import cycle. The gc callers inject the provider's program factory
> instead (see `_program_for` in `main.py`).

## `utils/watchdog.py`

Session TTL watchdog: schedules an OS-level one-shot that runs
`wisp destroy <provider> <region>` when the session TTL expires, so a
forgotten session cannot keep a billable VM running after Wisp exits.

- `schedule_ttl_watchdog(provider, region, ttl_minutes) -> str | None` —
  schedules the timer (best effort: failures are logged and return `None`,
  never raised). Idempotent: cancels any pending timer for the same target
  first (re-arming the session guard schedules the same name again).
- `cancel_ttl_watchdog(provider, region)` — cancels the timer (best effort,
  safe when nothing was scheduled or it already fired).
- `get_watchdog_task_name(provider, region) -> str` — deterministic name
  (`wisp-ttl-<provider>-<region>`) so any process can cancel the same timer.
- `watchdog_available() -> bool` — whether the platform scheduler binary is
  reachable.

Platform schedulers: `systemd-run --user` (Linux, transient one-shot unit) and
`schtasks /SC ONCE` (Windows). Other platforms log-and-skip.

## `utils/platform.py`

- `PlatformEnum(StrEnum)`: `LINUX`, `WINDOWS`, `MACOS`; `get_platform()` maps
  `platform.system()` to the enum.
- `secure_file(path, platform_enum=None)` — restricts a sensitive file:
  `0600` (owner-only) on Linux/macOS; on Windows, `icacls` with well-known SIDs
  (`*S-1-5-18:F` for SYSTEM, `*S-1-5-32-544:F` for Administrators) because
  account names are localized on non-English Windows installations.

## `utils/randoms.py`

- `get_random_generator() -> random.Random` — returns `random.SystemRandom()`.
- `get_wireguard_port() -> int` — random port in `49152–65535`.

## `utils/logger.py`

- `setup_logger(name) -> logging.Logger` — picks the sink by process type:
  - **Daemon mode** (`WISP_DAEMON=1`, set process-locally by importing
    `wisp.daemon`, and not Windows): a single stderr `StreamHandler` at
    `DEBUG`, no file handler, and no directory creation. Journald captures
    the service's stderr under systemd, and it is the multi-writer-safe sink
    (Python `logging` is thread-safe but not process-safe, so a root daemon
    must not rotate a file). Query with `journalctl -u wisp.service`.
  - **User processes** (TUI/CLI, and the Windows daemon whose service
    wrapper sets `WISP_LOG_DIR` process-locally): a rotating file handler
    (`WISP_LOG_DIR/wisp.log`, 5 MB × 3, `DEBUG`) and a stderr handler
    (`ERROR`), attached in that order — handler index `1` is the console
    handler, raised to `DEBUG` in CLI mode.
- `logger` — the configured `"wisp"` logger.

The log directory resolves from `WISP_LOG_DIR` with a truthiness guard: an
empty-string value falls back to the platformdirs default instead of
resolving to the current working directory. The directory is created only in
the file branch. Propagation disabled to avoid duplicates.
