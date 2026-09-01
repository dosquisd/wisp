import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def render_inventory_template(
    template_path: str | Path, output_path: str | Path, context: dict, mode: int = 0o644
) -> None:
    """
    Render the Ansible inventory template using Jinja2.

    Args:
        template_path (str | Path): Path to the Jinja2 template file.
        output_path (str | Path): Path where the rendered inventory will be saved.
        context (dict): Dictionary containing variables to be replaced in the template.
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


if __name__ == "__main__":
    # Example usage
    template_path = Path("templates/inventory.ini.j2")
    output_path = Path("inventory/inventory.ini.bak")
    context = {
        "ssh_user": "ubuntu",
        "instance_ip": "0.0.0.0",
        "ssh_key_file": "/path/to/your/private/key.pem",
        "wireguard_port": 51820,
        "allowed_ips": "0.0.0.0/0,::/0",
        "wireguard_public_ip": "0.0.0.0",
        "wireguard_interface": "wg0",
        "wireguard_ipv4": "0.0.0.0",
        "wireguard_ipv6": "fd42:42:42::1",
        "wireguard_dns1": "1.1.1.1",
        "wireguard_dns2": "1.0.0.1",
        "wireguard_client_name": "",
        "wireguard_client_ipv4": "",
        "wireguard_client_ipv6": "",
        "wireguard_skip_client": "n",
    }

    render_inventory_template(template_path, output_path, context)
