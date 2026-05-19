import sys
import subprocess
import os
import stat
import platform
from importlib.resources import files

def main():
    # 1. Detect local OS and architecture
    os_type = platform.system().lower()
    arch = platform.machine()
    
    # Standardize keys
    if os_type == "darwin":
        cpu_key = "arm64" if "arm" in arch.lower() else "amd64"
        platform_key = f"darwin-{cpu_key}"
        bin_name = f"toolbox-darwin-{cpu_key}"
    elif os_type == "windows":
        platform_key = "windows-amd64"
        bin_name = "toolbox-windows-amd64.exe"
    else:
        platform_key = "linux-amd64"
        bin_name = "toolbox-linux-amd64"
        
    # 2. Locate the embedded binary inside the virtual environment
    bin_path = files("mcp_toolbox").joinpath(f"bin/{bin_name}")

    if not bin_path.exists():
        print(f"Error: Go binary for platform {platform_key} not packaged in this wheel.", file=sys.stderr)
        sys.exit(1)

    bin_path_str = str(bin_path)

    # 3. Make sure execution permissions are set
    if os_type != "windows":
        try:
            current_stat = os.stat(bin_path_str)
            os.chmod(bin_path_str, current_stat.st_mode | stat.S_IEXEC)
        except Exception as e:
            print(f"Warning: Failed to set execution permissions: {e}", file=sys.stderr)

    # 4. Strip Apple Quarantine attributes on macOS
    if os_type == "darwin":
        try:
            subprocess.run(
                ["xattr", "-d", "com.apple.quarantine", bin_path_str],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    # 5. Proxy execution directly, preserving arguments, standard flows, and exit codes
    try:
        if os_type != "windows":
            os.execv(bin_path_str, [bin_path_str] + sys.argv[1:])
        else:
            result = subprocess.run([bin_path_str] + sys.argv[1:])
            sys.exit(result.returncode)
    except Exception as e:
        print(f"Error executing Go binary: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
