"""Download a URL to a file with progress, using Python's OpenSSL stack.

Windows schannel clients fail here (SEC_E_NO_CREDENTIALS under the sandbox), but
OpenSSL-based clients work, which is why npm and Python can reach the network.
"""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path


def main() -> int:
    url = sys.argv[1]
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "dsh-fetch/1.0"})
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(req, timeout=120) as resp:
        expected = resp.headers.get("Content-Length")
        expected = int(expected) if expected and expected.isdigit() else 0
        print(f"status {resp.status} content-length {expected}", flush=True)
        with out.open("wb") as fh:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
                digest.update(chunk)
                total += len(chunk)
                if expected:
                    pct = total * 100 // expected
                    if total % (32 * 1024 * 1024) < 1024 * 1024:
                        print(f"  {total / 1048576:7.1f} / {expected / 1048576:7.1f} MB ({pct}%)", flush=True)
    print(f"done {total} bytes -> {out}")
    print(f"sha256 {digest.hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
