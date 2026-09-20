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

- `setup_logger(name) -> logging.Logger` — a logger with a rotating file handler
  (`logs/wisp.log`, 5 MB × 5, `DEBUG`) and a stderr handler (`ERROR`).
  Propagation disabled to avoid duplicates.
- `logger` — the configured `"wisp"` logger (handler index `1` is the console
  handler, raised to `DEBUG` in CLI mode).
