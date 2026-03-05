import os
import sys
import subprocess
import pathlib
import plistlib

PLIST_NAME = "com.nova.daemon.plist"
LABEL = "com.nova.daemon"

def get_paths():
    home_dir = pathlib.Path.home()
    plist_path = home_dir / "Library" / "LaunchAgents" / PLIST_NAME
    log_dir = home_dir / "Library" / "Logs" / "nova"
    stdout_path = log_dir / "nova.log"
    stderr_path = log_dir / "nova_error.log"
    
    # Auto-detect path to the main executable (main.py in the root directory)
    script_dir = pathlib.Path(__file__).parent.resolve()
    nova_main = script_dir.parent / "main.py"
    
    return plist_path, log_dir, stdout_path, stderr_path, nova_main

def install():
    print("Installing N.O.V.A as a persistent macOS background service...")
    
    plist_path, log_dir, stdout_path, stderr_path, nova_main = get_paths()
    
    # 1. LOG DIRECTORY
    print(f"Ensuring log directory exists at: {log_dir}")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. PLIST GENERATION
    print(f"Generating launchd plist at: {plist_path}")
    plist_dict = {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, str(nova_main)],
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(stdout_path),
        "StandardErrorPath": str(stderr_path),
        "EnvironmentVariables": {
            "PYTHONUNBUFFERED": "1"
        }
    }
    
    # Ensure LaunchAgents directory exists
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(plist_path, "wb") as f:
        plistlib.dump(plist_dict, f)
        
    print("Plist generated successfully.")
    
    # 3. INSTALL
    print("Loading launchd service...")
    subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True) # suppress errors
    
    load_result = subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True, text=True)
    if load_result.returncode != 0:
        print(f"Failed to load service: {load_result.stderr}")
        return
        
    # 4. VERIFY
    print("Verifying service is running...")
    verify_result = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    
    # Find matching launchd instance and print output
    lines = [line for line in verify_result.stdout.splitlines() if LABEL in line]
    if lines:
        for line in lines:
            print(f"Match found: {line}")
        print("Install complete! N.O.V.A daemon is now running in the background.")
    else:
        print("Warning: Service was loaded but could not be verified via 'launchctl list'.")
        
def uninstall():
    print("Uninstalling N.O.V.A background service...")
    
    plist_path, _, _, _, _ = get_paths()
    
    print(f"Unloading launchd service from: {plist_path}")
    subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
    
    if plist_path.exists():
        print(f"Deleting plist file: {plist_path}")
        plist_path.unlink()
        print("Uninstall complete! N.O.V.A daemon is no longer running.")
    else:
        print("Service was not installed (plist not found).")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        uninstall()
    else:
        install()
