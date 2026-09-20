# `wisp.main` — entry point

File: `src/wisp/main.py`. Console script: `wisp = "wisp.main:main"`.

## Types

- `CommandEnum(StrEnum)`: `TUI`, `DEPLOY`, `DESTROY`, `REGIONS`.
- `RuntimeArgs(TypedDict)`: `{command: CommandEnum, provider: ProviderEnum | None, region: str | None}`.

## `parse_args() -> RuntimeArgs`

Builds an argparse parser:

- A shared `provider_parser` with an optional positional `provider` (choices
  from `ProviderEnum`, default from `get_default_provider()`).
- Subcommands: `deploy` and `destroy` (each with `-r/--region`, default `None`
  — the region is resolved from the provider's configured credentials) and
  `regions`.

Normalizes `command`, `provider`, and `region` to lowercase. If no subcommand is
given, `command` defaults to `CommandEnum.TUI`.

## `_create_provider_with_credentials(provider) -> BaseProvider`

Resolves the provider credentials first (`resolve_aws_credentials()` or
`resolve_oci_credentials()`) and instantiates the provider from
`PROVIDERS_MAP` with them.

## `main() -> None`

Dispatch:

- `TUI`: run `WispApp().run()` and exit `0`.
- Otherwise: raise the console log handler to `DEBUG`, assert a provider is
  present, and instantiate it with resolved credentials.
  - `REGIONS`: print `provider.get_available_regions()` as JSON.
  - `DEPLOY`/`DESTROY`: if no region was passed, resolve it from
    `provider.credentials.region` (the provider's configured region), then call
    `provider.deploy_vm(region=...)` or `provider.delete_vm(region=...)` and
    print the result.

The `assert` statements are defensive; argparse guarantees a provider in
practice, and the region falls back to the provider configuration.
