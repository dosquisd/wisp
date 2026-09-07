# Contributing

## Code layout

Source lives under `src/wisp/` (a `src`-layout package). See
[architecture.md](./architecture.md#package-layout) for the module map.

## Tooling

- Python **3.14+**.
- Dependency management with [`uv`](https://docs.astral.sh/uv/) (`uv.lock`).
- Linting/formatting with **Ruff** (`ruff>=0.16.5` in the `dev` group).
  Configured in `pyproject.toml`:
  - line length 88, 4-space indent, double quotes;
  - lint rules `E4, E7, E9, F` + import sorting (`I`).

Typical commands:

```bash
uv sync                 # install deps (incl. dev group)
uv run ruff check .     # lint
uv run ruff format .    # format
uv tool install --editable .   # install the `wisp` CLI
```

## Adding a cloud provider

The provider abstraction is designed for extension.

1. Create `src/wisp/providers/<name>/` with a class implementing
   `BaseProvider` (`providers/base.py`):
   - `get_available_regions() -> Sequence[str]`
   - `deploy_vm(region, force_current_ip=False, config=None, on_progress=None) -> DeployVMResult`
   - `delete_vm(region, on_progress=None) -> int`
2. Add a value to `ProviderEnum` and register the class in `PROVIDERS_MAP`
   (`providers/__init__.py`).
3. Reuse the shared building blocks where possible: `WispConfig`, the
   `InventoryContext` + Ansible flow (`wireguard/remote_server.py`), and the
   local client (`wireguard/local_client.py`).
4. Follow the deploy contract: provision → wait for boot → persist SSH key →
   render inventory → run Ansible → connect the local client. See
   [deployment flow](./deployment-flow.md).

The TUI's `DeployScreen` currently hardcodes AWS as the only provider option; a
new provider would also need to be surfaced there.

## Documentation

Docs live in `docs/`. Keep them in sync with the code they describe and prefer
linking to the [components reference](./components/README.md) over duplicating
signatures.

## Commits and pull requests

The history uses Conventional Commits (`feat:`, `fix:`, `refactor:`, `style:`,
`chore:`, `docs:`). Match that style. Open pull requests against `main`.
