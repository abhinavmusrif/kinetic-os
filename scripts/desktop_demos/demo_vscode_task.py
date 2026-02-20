import json
import os
import sys
from pathlib import Path

from os_controller.windows_controller import WindowsController

def main() -> None:
    if sys.platform != "win32":
        print("Skipping: Not on Windows.")
        return
        
    wc = WindowsController(allow_os_automation=True)
    
    print("Starting VSCode Task...")
    
    tasks = [
        {"action": "open_app", "name": "code"},
        {"action": "wait", "seconds": 4.0},
        {"action": "hotkey", "keys": ["ctrl", "shift", "p"]},
        {"action": "wait", "seconds": 1.0},
        {"action": "type", "text": "Toggle Terminal"},
        {"action": "wait", "seconds": 1.0},
        {"action": "hotkey", "keys": ["enter"]},
        {"action": "wait", "seconds": 2.0},
        # Check for change
        {"action": "assert", "target": {"text": "Terminal"}, "max_attempts": 3},
        {"action": "wait", "seconds": 1.0},
        {"action": "hotkey", "keys": ["alt", "f4"]}
    ]
    
    results = []
    for t in tasks:
        print(f"Executing: {t['action']}")
        res = wc.execute_task(t)
        results.append({"task": t, "result": res})
        if not res["success"] and t["action"] not in ("hotkey", "wait", "open_app"):
            print(f"Task failed: {res['reason']}")
            break
            
    # Save report
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    report_path = logs_dir / "vscode_demo_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"Demo complete. Report saved to {report_path}")

if __name__ == "__main__":
    main()
