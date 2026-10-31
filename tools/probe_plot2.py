"""Call parse_plot directly on the plot agent payload and report failures."""
from __future__ import annotations

import sys
from pathlib import Path

import profsave3 as p


def main() -> int:
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    header_block, data_block, info = p.unwrap(raw)
    s = p.load(path)
    for a in s.agents:
        off = a.offsets[1]
        if not off:
            continue
        r = p.BitReader(data_block, off, len(data_block) * 8 - off)
        size = r.u32(24)
        payload_start = r.pos
        probe = p.BitReader(data_block, payload_start, size)
        head = p.BitReader(data_block, payload_start, min(size, 512)).bytes_(min(60, size // 8))
        if b"BioMetrics_PlotStartMarker" not in head:
            continue
        print(f"agent {a.index} slot 1 offset {off} size {size}")
        try:
            plot = p.parse_plot(probe)
            print(f"  parsed: version {plot['version']} bools {len(plot['bools'])} ints {len(plot['ints'])} "
                  f"floats {len(plot['floats'])} transforms {len(plot['transforms'])} unknown {len(plot['unknown'])}")
        except p.SaveFormatError as e:
            print(f"  parse_plot failed: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
