import argparse
import enum
import json
import logging
import sys
from typing import TypedDict

from wisp.cli.app import WispApp
from wisp.providers import PROVIDERS_MAP, ProviderEnum
from wisp.utils.logger import logger


class CommandEnum(enum.StrEnum):
    TUI = "tui"
    DEPLOY = "deploy"
    DESTROY = "destroy"
    REGIONS = "regions"


class RuntimeArgs(TypedDict):
    command: CommandEnum
    provider: ProviderEnum | None
    region: str | None


def parse_args() -> RuntimeArgs:
    parser = argparse.ArgumentParser(description="Wisp CLI")

    # Parser for provider argument, which is common to all commands
    provider_parser = argparse.ArgumentParser(add_help=False)
    provider_parser.add_argument(
        "provider",
        nargs="?",
        type=str,
        choices=[provider.value for provider in ProviderEnum],
        default=ProviderEnum.AWS.value,
        help="Cloud provider to use (default %(default)s).",
    )

    # Subparsers for different commands
    subparsers = parser.add_subparsers(dest="command")

    deploy_parser = subparsers.add_parser(
        "deploy",
        parents=[provider_parser],
        help="Deploy a VM",
    )
    deploy_parser.add_argument(
        "-r",
        "--region",
        type=str,
        default="us-east-2",
        help="Region where the VM will be deployed (default %(default)s).",
    )

    destroy_parser = subparsers.add_parser(
        "destroy",
        parents=[provider_parser],
        help="Destroy VMs",
    )
    destroy_parser.add_argument(
        "-r",
        "--region",
        type=str,
        default="us-east-2",
        help="Region from which VMs will be destroyed (default %(default)s).",
    )

    subparsers.add_parser(
        "regions",
        parents=[provider_parser],
        help="List available regions",
    )

    args = parser.parse_args().__dict__

    return RuntimeArgs(
        command=(
            args["command"].lower()
            if args.get("command") is not None
            else CommandEnum.TUI
        ),
        provider=(
            ProviderEnum(args["provider"].lower())
            if args.get("provider") is not None
            else None
        ),
        region=args["region"].lower() if args.get("region") is not None else None,
    )


if __name__ == "__main__":
    args = parse_args()
    command = args["command"]
    region = args["region"]
    provider_option = args["provider"]

    if command == CommandEnum.TUI:
        app = WispApp()
        app.run()
        sys.exit(0)

    # Set console handler to DEBUG level for CLI mode
    logger.handlers[1].setLevel(logging.DEBUG)

    # It's not necessary to do this assertion, because the CLI will always provide a provider, but it's a good safety check
    assert provider_option is not None, (
        "Provider must be specified for deploy, destroy, or regions commands."
    )
    provider = PROVIDERS_MAP[provider_option]()

    if command == CommandEnum.REGIONS:
        logger.info(f"Fetching available regions for provider: {provider_option.value}")
        regions = provider.get_available_regions()
        print(f"Available regions:\n{json.dumps(regions, indent=2)}")
        sys.exit(0)

    # It's not neccesary to do this assertion, because the CLI will always provide a region, but it's a good safety check
    assert region is not None, (
        "Region must be specified for deploy or destroy commands."
    )

    logger.info(
        f"Running in CLI mode with command: {command}. "
        f"Provider: {provider_option.value}, Region: {region}"
    )

    if command == CommandEnum.DEPLOY:
        vm_result = provider.deploy_vm(region=region)
        print(f"Deployed VM:\n{json.dumps(vm_result, indent=2)}")
        sys.exit(0)

    if command == CommandEnum.DESTROY:
        delete_success = provider.delete_vm(region=region)
        print(f"Deleted VM. Count: {delete_success}")
        sys.exit(0)
