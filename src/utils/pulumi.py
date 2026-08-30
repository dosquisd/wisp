from pulumi import automation as auto

from src.config.constants import PULUMI_PROJECT_NAME, PULUMI_STACK_NAME


def create_or_select_pulumi_stack(
    program: auto.PulumiFn | None = None,
    *,
    stack_name: str = PULUMI_STACK_NAME,
    project_name: str = PULUMI_PROJECT_NAME,
) -> auto.Stack:
    return auto.create_or_select_stack(
        stack_name=stack_name, project_name=project_name, program=program
    )
