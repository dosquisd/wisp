from pulumi import automation as auto

from wisp.config.constants import PULUMI_PROJECT_NAME, PULUMI_STACK_NAME


def create_or_select_pulumi_stack(
    program: auto.PulumiFn | None = None,
    *,
    stack_name: str = PULUMI_STACK_NAME,
    project_name: str = PULUMI_PROJECT_NAME,
) -> auto.Stack:
    """Create or select the Pulumi stack via the Automation API.

    Args:
        program (auto.PulumiFn | None): The inline Pulumi program to run.
        stack_name (str): Stack name (defaults to ``wisp-stack``).
        project_name (str): Project name (defaults to ``wisp-project``).

    Returns:
        auto.Stack: The created or selected stack.
    """
    return auto.create_or_select_stack(
        stack_name=stack_name, project_name=project_name, program=program
    )
