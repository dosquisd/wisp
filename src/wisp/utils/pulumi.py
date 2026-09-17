from pulumi import automation as auto

from wisp.config.constants import PULUMI_PROJECT_NAME, get_pulumi_stack_name


def create_or_select_pulumi_stack(
    program: auto.PulumiFn | None = None,
    *,
    provider: str = "aws",
    project_name: str = PULUMI_PROJECT_NAME,
) -> auto.Stack:
    """Create or select the Pulumi stack via the Automation API.

    Args:
        program (auto.PulumiFn | None): The inline Pulumi program to run.
        provider (str): Cloud provider name (e.g., "aws", "oci"). Used to generate
            provider-specific stack name.
        project_name (str): Project name (defaults to ``wisp-project``).

    Returns:
        auto.Stack: The created or selected stack.
    """
    stack_name = get_pulumi_stack_name(provider)
    return auto.create_or_select_stack(
        stack_name=stack_name, project_name=project_name, program=program
    )
