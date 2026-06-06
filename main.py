"""Myorii application entry point."""

from __future__ import annotations

import platform


def main() -> None:
    if platform.system() == "Darwin":
        from platform.macos.menubar import run_menubar_app

        run_menubar_app()
        return

    raise RuntimeError(f"Myorii menu bar is not implemented for {platform.system()}")


if __name__ == "__main__":
    main()
