# This is far to be completed. There is some crucial details missing:
# 1. Architecture design. Currently, the code only supports one Virtual Machine (VM) per stack,
# the idea is to support multiple VMs per stack. This requires a more complex architecture design and an more
# appropiate state management, the current implementation is not scalable and does not work with multiple VMs.
# 2. For the same reason, the delete_vm must be refactored to support deleting a specific VM from the stack,
# instead of destroying the entire stack.
# 3. Same as delete_vm, there should be a method to stop a specific VM, instead of stopping the entire stack.

from collections.abc import Sequence

import boto3

from src.providers.aws.constants import DEFAULT_REGION
from src.providers.aws.pulumi import create_ec2_instance
from src.providers.base import BaseProvider, DeployVMResult
from src.utils import create_or_select_pulumi_stack, logger


class AWSProvider(BaseProvider):
    def __create_pulumi_program(self, region: str) -> None:
        create_ec2_instance(region)

    def get_available_regions(self) -> Sequence[str]:
        client = boto3.client("ec2", region_name=DEFAULT_REGION)
        return [r["RegionName"] for r in client.describe_regions()["Regions"]]

    def deploy_vm(self, region: str) -> DeployVMResult:
        stack = create_or_select_pulumi_stack(
            lambda: self.__create_pulumi_program(region)
        )
        up_result = stack.up()
        return DeployVMResult(
            instance_id=up_result.outputs["instance_id"].value,
            public_ip=up_result.outputs["instance_public_ip"].value,
            private_ip=up_result.outputs["instance_private_ip"].value,
        )

    def delete_vm(self, region: str, instance_id: str) -> bool:
        stack = create_or_select_pulumi_stack(
            lambda: self.__create_pulumi_program(region)
        )

        try:
            destroy_result = stack.destroy()
            print(destroy_result.summary.resource_changes)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error destroying stack: {e}")
            return False

        return True
