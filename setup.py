import sys
import os
import urllib.request
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py

VERSION = "1.2.0"
GCS_BASE_URL = "https://storage.googleapis.com/mcp-toolbox-for-databases"

class CustomBuildPy(build_py):
    """Intercepts 'python3 -m build' to download Go binaries from GCS and embed them."""
    def run(self):
        # 1. Run the standard build process to copy files to the build directory
        super().run()
        
        # 2. Create the target binary folder inside the packaging build directory
        build_lib = Path(self.build_lib) / "mcp_toolbox" / "bin"
        build_lib.mkdir(parents=True, exist_ok=True)
        
        # 3. Download target platform precompiled binaries from GCS
        platforms = {
            "darwin-arm64": "darwin/arm64/toolbox",
            "darwin-amd64": "darwin/amd64/toolbox",
            "linux-amd64": "linux/amd64/toolbox",
            "windows-amd64": "windows/amd64/toolbox.exe"
        }
        
        for platform_name, gcs_path in platforms.items():
            url = f"{GCS_BASE_URL}/v{VERSION}/{gcs_path}"
            target_file = build_lib / f"toolbox-{platform_name}"
            if platform_name.startswith("windows"):
                target_file = build_lib / f"toolbox-{platform_name}.exe"
                
            print(f"Embedding precompiled Go binary for {platform_name} from GCS...", file=sys.stderr)
            try:
                urllib.request.urlretrieve(url, target_file)
                # Grant executable rights (on macOS and Linux)
                if not platform_name.startswith("windows"):
                    os.chmod(target_file, 0o755)
            except Exception as e:
                print(f"Error fetching binary for {platform_name}: {e}", file=sys.stderr)
                raise e

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
