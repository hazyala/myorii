"""Platform-specific integrations plus stdlib platform compatibility.

The project keeps OS-dependent code under ``platform/``. Because that package
name shadows Python's standard-library ``platform`` module, expose the stdlib
module's public API here so dependencies can still call helpers like
``platform.system()``.
"""

from __future__ import annotations

import importlib.util
import sys
import sysconfig
from pathlib import Path


def _load_stdlib_platform() -> object:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        stdlib_path = Path(sys._MEIPASS) / "stdlib" / "platform.py"
    else:
        stdlib_path = Path(sysconfig.get_path("stdlib")) / "platform.py"

    spec = importlib.util.spec_from_file_location("_stdlib_platform", stdlib_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load Python stdlib platform module from {stdlib_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_stdlib_platform = _load_stdlib_platform()

for _name in dir(_stdlib_platform):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_stdlib_platform, _name)


__all__ = [name for name in globals() if not name.startswith("_")]
