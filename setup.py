import sys
import os
import urllib.request
import platform
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from wheel.bdist_wheel import bdist_wheel

VERSION = "1.2.0"
GCS_BASE_URL = "https://storage.googleapis.com/mcp-toolbox-for-databases"

# Supported target configurations
PLATFORM_MAPS = {
    "darwin-arm64": {
        "gcs_path": "darwin/arm64/toolbox",
        "bin_name": "toolbox-darwin-arm64",
        "wheel_tag": "macosx_11_0_arm64"
    },
    "darwin-amd64": {
        "gcs_path": "darwin/amd64/toolbox",
        "bin_name": "toolbox-darwin-amd64",
        "wheel_tag": "macosx_10_9_x86_64"
    },
    "linux-amd64": {
        "gcs_path": "linux/amd64/toolbox",
        "bin_name": "toolbox-linux-amd64",
        "wheel_tag": "manylinux2014_x86_64"
    },
    "windows-amd64": {
        "gcs_path": "windows/amd64/toolbox.exe",
        "bin_name": "toolbox-windows-amd64.exe",
        "wheel_tag": "win_amd64"
    }
}

def get_target_platform():
    """Resolves the target platform from environment variables or auto-detects local host."""
    target = os.environ.get("MCP_TOOLBOX_PLATFORM")
    if target:
        if target not in PLATFORM_MAPS:
            raise ValueError(f"Unsupported target platform override: '{target}'. Must be one of: {list(PLATFORM_MAPS.keys())}")
        return target
        
    # Fallback to auto-detection
    os_type = platform.system().lower()
    arch = platform.machine()
    
    if os_type == "darwin":
        cpu_key = "arm64" if "arm" in arch.lower() else "amd64"
        return f"darwin-{cpu_key}"
    elif os_type == "windows":
        return "windows-amd64"
    else:
        return "linux-amd64"

TARGET_PLATFORM = get_target_platform()
PLATFORM_CONFIG = PLATFORM_MAPS[TARGET_PLATFORM]

class CustomBuildPy(build_py):
    """Intercepts 'python3 -m build' to download only the target Go binary from GCS."""
    def run(self):
        # 1. Run standard copy
        super().run()
        
        # 2. Create the target bin directory
        build_lib = Path(self.build_lib) / "mcp_toolbox" / "bin"
        build_lib.mkdir(parents=True, exist_ok=True)
        
        # 3. Download ONLY the matching target Go binary
        gcs_path = PLATFORM_CONFIG["gcs_path"]
        bin_name = PLATFORM_CONFIG["bin_name"]
        
        url = f"{GCS_BASE_URL}/v{VERSION}/{gcs_path}"
        target_file = build_lib / bin_name
            
        print(f"[{TARGET_PLATFORM}] Downloading and embedding native Go binary from GCS...", file=sys.stderr)
        try:
            urllib.request.urlretrieve(url, target_file)
            # Set executable privileges on Unix
            if not TARGET_PLATFORM.startswith("windows"):
                os.chmod(target_file, 0o755)
        except Exception as e:
            print(f"Error fetching binary for {TARGET_PLATFORM}: {e}", file=sys.stderr)
            raise e

class CustomBdistWheel(bdist_wheel):
    """Forces setuptools to compile a platform-specific native wheel instead of pure-Python."""
    def get_tag(self):
        # Return the native PEP 425 tag matching our target Go binary
        tag = PLATFORM_CONFIG["wheel_tag"]
        return "py3", "none", tag

setup(
    name="mcp-toolbox",
    version=VERSION,
    description="Python wrapper for the MCP Toolbox for Databases Go binary server",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="Google LLC",
    author_email="googleapis-packages@google.com",
    url="https://github.com/googleapis/mcp-toolbox",
    packages=find_packages(where="uv/src"),
    package_dir={"": "uv/src"},
    cmdclass={
        'build_py': CustomBuildPy,
        'bdist_wheel': CustomBdistWheel, # Forces correct platform tags (e.g. win_amd64, manylinux2014_x86_64)
    },
    entry_points={
        'console_scripts': [
            'toolbox=mcp_toolbox.cli:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10"
)
