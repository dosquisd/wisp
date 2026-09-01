import json
import sys

from src.providers.aws import AWSProvider

if __name__ == "__main__":
    provider = AWSProvider()

    if len(sys.argv) < 2:
        vm_result = provider.deploy_vm(region="us-east-2")
        print(f"Deployed VM:\n{json.dumps(vm_result, indent=2)}")
        sys.exit(0)

    if sys.argv[1].lower() in {"delete", "destroy"}:
        delete_success = provider.delete_vm(region="us-east-2")
        print(f"Deleted VM. Count: {delete_success}")
        sys.exit(0)

    sys.exit(1)
