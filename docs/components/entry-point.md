# `wisp.main` — entry point

File: `src/wisp/main.py`. Console script: `wisp = "wisp.main:main"`.

## Types

- `CommandEnum(StrEnum)`: `TUI`, `DEPLOY`, `DESTROY`, `REGIONS`.
- `RuntimeArgs(TypedDict)`: `{command: CommandEnum, provider: ProviderEnum | None, region: str | None}`.

## `parse_args() -> RuntimeArgs`

Builds an argparse parser:

- A shared `provider_parser` with an optional positional `provider` (choices from
  `ProviderEnum`, default `aws`).
- Subcommands: `deploy` and `destroy` (each with `-r/--region`, default
  `us-east-2`) and `regions`.

Normalizes `command`, `provider`, and `region` to lowercase. If no subcommand is
given, `command` defaults to `CommandEnum.TUI`.

## `main() -> None`

Dispatch:

- `TUI`: run `WispApp().run()` and exit `0`.
- Otherwise: raise the console log handler to `DEBUG`, assert a provider is
  present, and instantiate it from `PROVIDERS_MAP`.
  - `REGIONS`: print `provider.get_available_regions()` as JSON.
  - `DEPLOY`: assert a region, call `provider.deploy_vm(region=...)`, print the
    result as JSON.
  - `DESTROY`: assert a region, call `provider.delete_vm(region=...)`, print the
    deleted count.

The `assert` statements are defensive; argparse guarantees a provider/region in
practice.
