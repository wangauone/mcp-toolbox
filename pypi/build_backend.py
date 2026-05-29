"""Custom PEP 517 build backend that produces one wheel per target platform.

A single `python -m build --wheel` invocation emits wheels for every entry in
TARGETS. Each iteration runs setuptools' build_wheel hook in a fresh
subprocess so distutils' per-process caches don't leak between targets. Env
vars tell setup.py which Go binary to download and which wheel platform tag
to stamp.
"""

import json
import os
import shutil
import subprocess
import sys

from setuptools.build_meta import (  # noqa: F401  re-export PEP 517 hooks
    build_sdist,
    get_requires_for_build_sdist,
    get_requires_for_build_wheel,
    prepare_metadata_for_build_wheel,
)

TARGETS = [
    # (TOOLBOX_TARGET_OS, TOOLBOX_TARGET_ARCH, wheel plat_name)
    ("linux",   "amd64", "manylinux2014_x86_64"),
    ("darwin",  "amd64", "macosx_10_9_x86_64"),
    ("darwin",  "arm64", "macosx_11_0_arm64"),
    ("windows", "amd64", "win_amd64"),
]


def _build_one(wheel_directory, config_settings, metadata_directory, target):
    os_part, arch_part, plat = target
    # Subprocesses don't share Python state, but disk state persists:
    # clear the previous iteration's build artifacts so stale binaries
    # from a prior target don't end up in this wheel.
    here = os.path.dirname(os.path.abspath(__file__))
    for d in ("build", "src/toolbox_server/bin"):
        path = os.path.join(here, d)
        if os.path.isdir(path):
            shutil.rmtree(path)
    env = os.environ.copy()
    env["TOOLBOX_TARGET_OS"] = os_part
    env["TOOLBOX_TARGET_ARCH"] = arch_part
    env["TOOLBOX_PLAT_NAME"] = plat
    script = (
        "import json, sys\n"
        "from setuptools.build_meta import build_wheel\n"
        "args = json.loads(sys.argv[1])\n"
        "print(build_wheel(*args))\n"
    )
    args = [wheel_directory, config_settings, metadata_directory]
    out = subprocess.check_output(
        [sys.executable, "-c", script, json.dumps(args)],
        env=env,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    return out.decode().strip().splitlines()[-1]


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    last = None
    for target in TARGETS:
        last = _build_one(wheel_directory, config_settings, metadata_directory, target)
    return last
