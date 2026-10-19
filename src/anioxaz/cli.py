from __future__ import annotations

import sys

from textual.app import App

from .core import APP_NAME


def main() -> int:
    try:
        from .app import AnioxazApp
    except ModuleNotFoundError as exc:
        if exc.name == "textual":
            print(
                "ANIOXAZ requires Textual. Install it with: python3 -m pip install -r requirements.txt",
                file=sys.stderr,
            )
            return 1
        raise
    app = AnioxazApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
