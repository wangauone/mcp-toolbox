import sys
import os
import urllib.request
import platform
import subprocess
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

class CustomBuildPy(build_py):
    """Child build step: downloads ONLY the single target platform Go binary from GCS."""
    def run(self):
        super().run()
        
        target_platform = os.environ.get("MCP_TOOLBOX_PLATFORM")
        if not target_platform:
            # Avoid downloading in parent sdist phase
            return
            
        config = PLATFORM_MAPS[target_platform]
        build_lib = Path(self.build_lib) / "mcp_toolbox" / "bin"
        build_lib.mkdir(parents=True, exist_ok=True)
        
        gcs_path = config["gcs_path"]
        bin_name = config["bin_name"]
        
        url = f"{GCS_BASE_URL}/v{VERSION}/{gcs_path}"
        target_file = build_lib / bin_name
            
        print(f"[{target_platform}] Downloading native Go binary from GCS...", file=sys.stderr)
        try:
            urllib.request.urlretrieve(url, target_file)
            if not target_platform.startswith("windows"):
                os.chmod(target_file, 0o755)
        except Exception as e:
            print(f"Error fetching binary for {target_platform}: {e}", file=sys.stderr)
            raise e

class CustomBdistWheel(bdist_wheel):
    """Orchestrates multiple platform builds or tags a single native wheel."""
    def run(self):
        target_platform = os.environ.get("MCP_TOOLBOX_PLATFORM")
        
        if not target_platform:
            # Parent Mode: Spawn clean, isolated subprocesses for each target platform
            print("Parent Build: Spawning isolated builds for all platform wheels...", file=sys.stderr)
            
            for plat in PLATFORM_MAPS.keys():
                wheel_tag = PLATFORM_MAPS[plat]["wheel_tag"]
                print(f"\n---> Spawning build for {plat} ({wheel_tag})...", file=sys.stderr)
                
                # Force absolute path resolution for dist-dir
                absolute_dist_dir = os.path.abspath(self.dist_dir)
                
                cmd = [
                    sys.executable, "setup.py",
                    "build", "--build-base", f"build/build-{plat}", # Isolate Go compilation/staging folders
                    "bdist_wheel",
                    "--bdist-dir", f"build/bdist-{plat}",
                    "--dist-dir", absolute_dist_dir,               # Forward PEP 517 compiler target directory
                    "--plat-name", wheel_tag
                ]
                subprocess.run(
                    cmd,
                    env={**os.environ, "MCP_TOOLBOX_PLATFORM": plat},
                    check=True
                )
            print("\nParent Build: All platform-specific wheels built successfully!", file=sys.stderr)
            return
            
        # Child Mode: Delegate to standard setuptools bdist_wheel
        super().run()

    def get_tag(self):
        # Ensures correct platform tag matching the current child target
        target_platform = os.environ.get("MCP_TOOLBOX_PLATFORM")
        if target_platform:
            tag = PLATFORM_MAPS[target_platform]["wheel_tag"]
            return "py3", "none", tag
        return super().get_tag()

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
        'bdist_wheel': CustomBdistWheel,
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
