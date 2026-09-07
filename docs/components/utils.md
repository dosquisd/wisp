# `wisp.utils`

Shared helpers. `utils/__init__.py` re-exports the common ones and uses module
`__getattr__` for lazy imports of the heavier Pulumi/Jinja helpers.

## Exports

`get_ansible_playbook_bin`, `get_public_ip`, `get_random_generator`,
`get_wireguard_port`, `logger`. Lazily via `__getattr__`:
`create_or_select_pulumi_stack`, `render_inventory_template`.

## `utils/__init__.py`

- `get_public_ip() -> str` — GETs `https://api.ipify.org`.
- `__getattr__(name)` — lazy-imports `create_or_select_pulumi_stack` and
  `render_inventory_template` on first access; raises `AttributeError` otherwise.

## `utils/ansible.py`

- `get_ansible_playbook_bin() -> str` — resolves `ansible-playbook`, preferring a
  global install on `PATH` (outside the current venv) over the venv binary.
  Raises `FileNotFoundError` with guidance if neither is found.
- Helpers: `_find_global_bin`, `_find_local_bin`, `_is_within`.

## `utils/pulumi.py`

- `create_or_select_pulumi_stack(program=None, *, stack_name=PULUMI_STACK_NAME, project_name=PULUMI_PROJECT_NAME) -> auto.Stack`
  — wraps `pulumi.automation.create_or_select_stack`.

## `utils/templates.py`

- `render_inventory_template(template_path, output_path, context, mode=0o644) -> None`
  — renders a Jinja2 template (loaded from `/` via `FileSystemLoader`) with the
  `InventoryContext` and writes the output with the given file mode.

## `utils/randoms.py`

- `get_random_generator() -> random.Random` — returns `random.SystemRandom()`.
- `get_wireguard_port() -> int` — random port in `49152–65535`.

## `utils/logger.py`

- `setup_logger(name) -> logging.Logger` — a logger with a rotating file handler
  (`logs/wisp.log`, 5 MB × 5, `DEBUG`) and a stderr handler (`ERROR`).
  Propagation disabled to avoid duplicates.
- `logger` — the configured `"wisp"` logger (handler index `1` is the console
  handler, raised to `DEBUG` in CLI mode).
