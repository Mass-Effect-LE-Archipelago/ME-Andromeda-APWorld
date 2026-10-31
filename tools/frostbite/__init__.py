"""tools.frostbite - a pure-Python 3.14 reader for Mass Effect Andromeda's
Frostbite container (layout.toc / .sb / .toc / cas.cat / .cas / EBX partitions).

Nothing here writes to or modifies the game install; every access is a bounded
read of an existing file.
"""
from __future__ import annotations

__all__ = ["__version__"]
__version__ = "1.0.0"
