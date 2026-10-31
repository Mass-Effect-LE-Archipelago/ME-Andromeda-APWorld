"""Read and rebuild a Frosty mod `.archive` (the payload companion of an FBMODV2 mod).

Layout, verified against `betterDeconstruction_01.archive` (920 chunks, 2.4 MB):

    repeat:
        u32be uncompressed size
        u16be constant 0x0F70          (compression/format marker)
        u16be compressed size
        bytes  zstd frame             (decompresses to an EBX partition, magic CE D1 B2 0F)

Rebuild is byte-identical when no chunk changes, so editing a chunk is just "replace its bytes and
update the two size fields".
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from compression import zstd

MARKER = 0x0F70
EBX_MAGIC = b"\xce\xd1\xb2\x0f"


class ArchiveError(Exception):
    pass


@dataclass
class Chunk:
    offset: int
    size: int          # uncompressed size, from the header
    marker: int
    compressed: bytes  # the zstd frame as stored
    data: bytes = b""  # decompressed payload


def parse(data: bytes, decompress: bool = True) -> list[Chunk]:
    chunks: list[Chunk] = []
    offset = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise ArchiveError(f"truncated header at 0x{offset:X}")
        size = int.from_bytes(data[offset:offset + 4], "big")
        marker = int.from_bytes(data[offset + 4:offset + 6], "big")
        comp_size = int.from_bytes(data[offset + 6:offset + 8], "big")
        start = offset + 8
        end = start + comp_size
        if marker != MARKER:
            raise ArchiveError(f"unexpected marker 0x{marker:04X} at 0x{offset:X}")
        if end > len(data):
            raise ArchiveError(f"chunk at 0x{offset:X} runs past the end")
        frame = data[start:end]
        chunk = Chunk(offset=offset, size=size, marker=marker, compressed=frame)
        if decompress:
            try:
                chunk.data = zstd.decompress(frame)
            except Exception as exc:  # noqa: BLE001
                raise ArchiveError(f"chunk at 0x{offset:X}: {exc}") from exc
            if len(chunk.data) != size:
                raise ArchiveError(f"chunk at 0x{offset:X}: {len(chunk.data)} != {size}")
        chunks.append(chunk)
        offset = end
    return chunks


def rebuild(chunks: list[Chunk]) -> bytes:
    out = bytearray()
    for chunk in chunks:
        out += len(chunk.data).to_bytes(4, "big")
        out += MARKER.to_bytes(2, "big")
        out += len(chunk.compressed).to_bytes(2, "big")
        out += chunk.compressed
    return bytes(out)


def replace(chunk: Chunk, data: bytes, level: int = 3) -> None:
    """Swap in new uncompressed bytes and recompress."""
    chunk.data = data
    chunk.compressed = zstd.compress(data, level)


def is_chunked(data: bytes) -> bool:
    """True for the chunked payload store; false for a raw blob (icons are plain PNG/JPEG)."""
    return len(data) >= 8 and int.from_bytes(data[4:6], "big") == MARKER


def main() -> int:
    import sys
    folder = Path(__file__).resolve().parent.parent.parent / "Mass Effect Andromeda Mods"
    archives = sorted(folder.glob("*.archive"))
    print(f"archives: {len(archives)}")
    identical = 0
    for path in archives:
        raw = path.read_bytes()
        if not is_chunked(raw):
            kind = "png" if raw[:4] == b"\x89PNG" else "jpg" if raw[:2] == b"\xff\xd8" else "raw"
            print(f"  RAW  {path.name[:40]:40s} {kind:4s} bytes {len(raw):9d}")
            identical += 1
            continue
        chunks = parse(raw)
        rebuilt = rebuild(chunks)
        same = rebuilt == raw
        identical += same
        print(f"  {'OK  ' if same else 'DIFF'} {path.name[:40]:40s} chunks {len(chunks):5d} "
              f"bytes {len(raw):9d} -> {len(rebuilt):9d}")
    print(f"verified {identical} of {len(archives)}")
    return 0 if identical == len(archives) else 1


if __name__ == "__main__":
    raise SystemExit(main())
