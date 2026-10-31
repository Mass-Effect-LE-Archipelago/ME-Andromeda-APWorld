"""Run the CLI without needing the package to be importable by name.

    python tools\\frostbite\\run.py guid game/plots/...
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frostbite.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
