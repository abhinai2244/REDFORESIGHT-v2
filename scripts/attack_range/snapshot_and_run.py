#!/usr/bin/env python3
"""
VM Automation Harness for RedForesight Attack Range.
Manages VirtualBox VM snapshot reverting, boots the VM, triggers attack chains, and retrieves ground truth logs.
"""

import sys
import json
import time
import subprocess
from pathlib import Path

def run_cmd(cmd):
    print(f"[CMD] {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] {res.stderr}")
    return res.stdout

def revert_and_run_chain(vm_name: str, snapshot_name: str, chain_name: str, output_path: str):
    print(f"Reverting VM '{vm_name}' to snapshot '{snapshot_name}'...")
    run_cmd(f"VBoxManage controlvm {vm_name} poweroff")
    time.sleep(2)
    run_cmd(f"VBoxManage snapshot {vm_name} restore {snapshot_name}")

    print(f"Starting VM '{vm_name}'...")
    run_cmd(f"VBoxManage startvm {vm_name} --type headless")
    time.sleep(10)

    print(f"Executing attack chain '{chain_name}' on victim VM...")
    ps_cmd = f"powershell.exe -ExecutionPolicy Bypass -File C:\\RedForesight\\run_attack_chain.ps1 -ChainName {chain_name} -LogPath C:\\RedForesight\\ground_truth.json"
    run_cmd(f'VBoxManage guestcontrol {vm_name} run --exe "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" --username "Administrator" --password "Password123!" -- {ps_cmd}')

    print("Retrieving ground truth JSON log...")
    run_cmd(f'VBoxManage guestcontrol {vm_name} copyfrom C:\\RedForesight\\ground_truth.json {output_path}')
    print(f"Attack chain execution completed. Ground truth saved to {output_path}")

if __name__ == "__main__":
    chain = sys.argv[1] if len(sys.argv) > 1 else "chain_a"
    out_file = sys.argv[2] if len(sys.argv) > 2 else "fixtures/ground_truth_chain_a.json"
    print(f"Simulating/Running attack chain harness for: {chain}")
    Path("fixtures").mkdir(exist_ok=True)
    if not Path(out_file).exists():
        fixture_data = {
            "chain_id": chain,
            "run_timestamp": "2026-07-15T14:00:00Z",
            "steps": [
                {"technique_id": "T1566.001", "executed_at": "2026-07-15T14:00:00Z", "host": "VICTIM-01"},
                {"technique_id": "T1059.001", "executed_at": "2026-07-15T14:02:30Z", "host": "VICTIM-01"},
                {"technique_id": "T1003.001", "executed_at": "2026-07-15T14:05:00Z", "host": "VICTIM-01"},
                {"technique_id": "T1021.002", "executed_at": "2026-07-15T14:08:00Z", "host": "VICTIM-01"}
            ]
        }
        with open(out_file, "w") as f:
            json.dump(fixture_data, f, indent=2)
        print(f"Created sample ground truth fixture at {out_file}")
