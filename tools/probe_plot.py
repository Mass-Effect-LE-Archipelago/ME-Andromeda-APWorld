"""Manually walk the plot agent payload with verbose positions (lenient frames)."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import profsave3 as p

PLOT_AGENT_OFFSET = None


def main() -> int:
    raw = Path(sys.argv[1]).read_bytes()
    header_block, data_block, info = p.unwrap(raw)
    s = p.load(Path(sys.argv[1]))

    target = None
    for a in s.agents:
        off = a.offsets[1]
        if not off:
            continue
        r = p.BitReader(data_block, off, len(data_block) * 8 - off)
        size = r.u32(24)
        head = p.BitReader(data_block, r.pos, min(size, 1024))
        b = head.bytes_(min(64, size // 8))
        if b"BioMetrics_PlotStartMarker" in b:
            target = (a.index, off, size, r.pos)
            break
    if target is None:
        print("plot agent not found")
        return 1
    idx, off, size, payload = target
    print(f"plot agent idx {idx} offset {off} bits, payload {size} bits at {payload}")

    r = p.BitReader(data_block, payload, size)
    outer = r.u32(24)
    print(f"  outer frame length {outer}  (expected end {payload + 24 + outer}, data bits {len(data_block) * 8})")
    inner = r.u32(24)
    print(f"  inner frame length {inner}  (expected end {r.pos + inner})")
    version = r.u16()
    marker = r.string()
    print(f"  version {version} marker {marker!r} pos {r.pos}")
    nbits = 31 if version >= 4 else 16
    false_count = r.u32(nbits)
    print(f"  falseCount {false_count} pos {r.pos}")
    for i in range(min(false_count, 3)):
        print("    false guid", r.guid())
    r.pos = r.pos + (false_count - min(false_count, 3)) * 128
    true_count = r.u32(nbits)
    print(f"  trueCount {true_count} pos {r.pos}")
    for i in range(min(true_count, 3)):
        print("    true guid", r.guid())
    r.pos = r.pos + (true_count - min(true_count, 3)) * 128
    int_count = r.u16()
    print(f"  intCount {int_count} pos {r.pos}")
    for i in range(min(int_count, 3)):
        print("    int", r.guid(), r.i32())
    r.pos = r.pos + (int_count - min(int_count, 3)) * 160
    float_count = r.u16()
    print(f"  floatCount {float_count} pos {r.pos}")
    for i in range(min(float_count, 3)):
        print("    float", r.guid(), r.f32())
    r.pos = r.pos + (float_count - min(float_count, 3)) * 160
    transform_count = r.u16()
    print(f"  transformCount {transform_count} pos {r.pos}")
    unknown_count = r.u16() if version >= 3 else 0
    print(f"  unknownCount {unknown_count} pos {r.pos}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
