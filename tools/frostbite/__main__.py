"""``python -m frostbite`` / ``python -m tools.frostbite`` entry point."""
from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
