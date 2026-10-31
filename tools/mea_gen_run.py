"""Run the real Archipelago generator inside the DSH workspace sandbox.

Two environment problems are worked around here, both documented so the run is honest:

1. The vendored venv lacks some unrelated worlds' third-party packages, so the official
   `SKIP_REQUIREMENTS_UPDATE=1` switch is used instead of its dependency gate.
2. The sandbox permits writes into directories that already exist, but denies writes into
   subdirectories created by the subprocess. Archipelago writes its output through
   `tempfile.TemporaryDirectory()`, which would create one, so that call is redirected to
   pre-created directories (made by the harness, one per output).

Usage:
  python tools/mea_gen_run.py <ap-root> <tmp-pool-dir> <generator args...>
"""
from __future__ import annotations

import itertools
import runpy
import sys
import tempfile
from pathlib import Path


class PrecreatedTemporaryDirectory:
    def __init__(self, *args, **kwargs):
        self.name = str(next(_POOL))
        path = Path(self.name)
        path.mkdir(parents=True, exist_ok=True)
        # The generator zips everything in this directory, so stale output from an earlier
        # run would leak into the new archive (that is how a 3259-location spoiler once
        # ended up inside a 1432-location seed).
        for child in path.iterdir():
            try:
                if child.is_file():
                    child.unlink()
                else:
                    import shutil
                    shutil.rmtree(child, ignore_errors=True)
            except OSError:
                pass

    def __enter__(self) -> str:
        return self.name

    def __exit__(self, *exc) -> bool:
        return False

    def cleanup(self) -> None:
        return None


def main() -> int:
    ap_root = Path(sys.argv[1]).resolve()
    pool_dir = Path(sys.argv[2]).resolve()
    pool_dir.mkdir(parents=True, exist_ok=True)
    slots = [pool_dir / f"out{i}" for i in range(1, 9)]
    global _POOL
    _POOL = itertools.cycle(slots)

    tempfile.TemporaryDirectory = PrecreatedTemporaryDirectory  # type: ignore[assignment]
    sys.path.insert(0, str(ap_root))
    sys.argv = ["Generate.py", *sys.argv[3:]]
    runpy.run_path(str(ap_root / "Generate.py"), run_name="__main__")
    return 0


_POOL = itertools.cycle([Path(".")])

if __name__ == "__main__":
    raise SystemExit(main())
