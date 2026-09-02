import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.cli.app import WispApp  # noqa: E402
from src.providers.aws import AWSProvider  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1].lower() in {"tui", "ui"}:
        app = WispApp()
        app.run()
        sys.exit(0)

    provider = AWSProvider()
    region = sys.argv[2] if len(sys.argv) > 2 else "us-east-2"

    if sys.argv[1].lower() in {"delete", "destroy"}:
        delete_success = provider.delete_vm(region=region)
        print(f"Deleted VM. Count: {delete_success}")
        sys.exit(0)

    if sys.argv[1].lower() in {"deploy"}:
        vm_result = provider.deploy_vm(region=region)
        print(f"Deployed VM:\n{json.dumps(vm_result, indent=2)}")
        sys.exit(0)

    print(f"Comando no reconocido: {sys.argv[1]}. Opciones: [tui | deploy | destroy]")
    sys.exit(1)
