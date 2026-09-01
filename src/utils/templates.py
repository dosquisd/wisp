import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.schemas import InventoryContext


def render_inventory_template(
    template_path: str | Path, output_path: str | Path, context: InventoryContext, mode: int = 0o644
) -> None:
    """
    Render the Ansible inventory template using Jinja2.

    Args:
        template_path (str | Path): Path to the Jinja2 template file.
        output_path (str | Path): Path where the rendered inventory will be saved.
        context (InventoryContext): Dictionary containing variables to be replaced in the template.
    """
    # Set up the Jinja2 environment
    if isinstance(template_path, str):
        template_path = Path(template_path)
    if isinstance(output_path, str):
        output_path = Path(output_path)

    template_path = template_path.absolute()
    output_path = output_path.absolute()

    env = Environment(loader=FileSystemLoader(searchpath="/"))
    template = env.get_template(str(template_path))

    # Render the template with the provided context
    rendered_content = template.render(**context)

    # Write the rendered content to the output file
    with open(output_path, "w", opener=lambda p, f: os.open(p, f, mode)) as f:
        f.write(rendered_content)
