import json
import time

from src.providers.aws import AWSProvider

if __name__ == "__main__":
    provider = AWSProvider()
    vm_result = provider.deploy_vm(region="us-east-1")
    print(f"Deployed VM:\n{json.dumps(vm_result, indent=2)}")

    time.sleep(10)  # Wait for a while before deleting the VM
    
    delete_success = provider.delete_vm(region="us-east-1", instance_id=vm_result["instance_id"])
    print(f"Deleted VM: {delete_success}")
