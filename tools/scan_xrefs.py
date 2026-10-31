"""Find code references to specific strings in a PE without a disassembler.

Scans .text for x86-64 RIP-relative `lea`/`mov` instructions and reports those whose
target lands inside a set of anchor strings discovered by the earlier string scan.
Enough to locate the save/plot serializer functions and then analyse them in Ghidra on
demand, instead of paying for a full-PE analysis up front.

Usage:
  python scan_xrefs.py <exe> [--anchor-hex 0x142fdd4f8 ...] [--anchor-string TEXT ...]
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

# REX.W LEA/MOV r64, [rip+disp32]: 48 8D /r  and  48 8B /r with modrm mod=00 rm=101
OPCODES = {0x8D: "lea", 0x8B: "mov"}


def parse_pe(data: bytes) -> dict:
    if data[:2] != b"MZ":
        raise SystemExit("not a PE")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise SystemExit("bad PE signature")
    machine, nsect = struct.unpack_from("<HH", data, pe + 4)
    optsize = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    image_base = struct.unpack_from("<Q", data, opt + 24)[0] if magic == 0x20B else \
        struct.unpack_from("<I", data, opt + 28)[0]
    sec_off = opt + optsize
    sections = []
    for i in range(nsect):
        o = sec_off + 40 * i
        name = data[o:o + 8].rstrip(b"\0").decode("latin-1")
        vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, o + 8)
        sections.append({"name": name, "vaddr": vaddr, "vsize": vsize,
                         "raw": rawptr, "rawsize": rawsize})
    return {"image_base": image_base, "sections": sections}


def find_strings(data: bytes, pe: dict, anchors: list[str]) -> dict[int, str]:
    """Return {virtual address: anchor text} for anchor strings in file data."""
    found = {}
    for anchor in anchors:
        raw = anchor.encode()
        idx = data.find(raw)
        while idx >= 0:
            va = file_to_va(idx, pe)
            if va is not None:
                found[va] = anchor
            idx = data.find(raw, idx + 1)
    return found


def file_to_va(off: int, pe: dict) -> int | None:
    for s in pe["sections"]:
        if s["raw"] <= off < s["raw"] + s["rawsize"]:
            return pe["image_base"] + s["vaddr"] + (off - s["raw"])
    return None


def va_to_file(va: int, pe: dict) -> int | None:
    rva = va - pe["image_base"]
    for s in pe["sections"]:
        if s["vaddr"] <= rva < s["vaddr"] + max(s["vsize"], s["rawsize"]):
            return s["raw"] + (rva - s["vaddr"])
    return None


def scan(data: bytes, pe: dict, targets: dict[int, str]) -> list[tuple[int, str, str]]:
    """Find RIP-relative instructions whose target is one of the anchors.

    Handles REX 0x40-0x4F prefixes and the common 32-bit forms. Only instructions with
    modrm mod=00, rm=101 are RIP-relative in 64-bit mode.
    """
    hits = []
    for s in pe["sections"]:
        if s["rawsize"] == 0 or "text" not in s["name"].lower():
            continue
        start, end = s["raw"], s["raw"] + s["rawsize"]
        i = start
        while i < end - 7:
            b = data[i]
            op_off = None
            prefix = ""
            if 0x40 <= b <= 0x4F and data[i + 1] in (0x8D, 0x8B, 0x89, 0x39, 0x3B, 0x3C, 0x3D):
                op_off = i + 1
                prefix = f"rex{b - 0x40:02b} "
            elif b in (0x8D, 0x8B, 0x89, 0x39, 0x3B):
                op_off = i
            if op_off is not None:
                modrm = data[op_off + 1]
                if (modrm & 0xC7) == 0x05:
                    disp = struct.unpack_from("<i", data, op_off + 2)[0]
                    insn_va = file_to_va(i, pe)
                    if insn_va is not None:
                        target = insn_va + (op_off - i) + 6 + disp
                        if target in targets:
                            hits.append((insn_va, prefix + OPCODES.get(data[op_off], hex(data[op_off])),
                                         targets[target]))
            i += 1
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("exe", type=Path)
    ap.add_argument("--anchor-string", action="append", default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    anchors = args.anchor_string or [
        "BioMetrics_PlotStartMarker", "PlotSaveGameAgent", "FBCHUNKS", "FBHEADER",
        "PlotFlagIds", "PlotFlagsDefaultValues", "NewGamePlusPlotFlags",
        "PlotFlagDebugSymbol", "LastPlotFlagSet", "IPlotFlag",
    ]
    data = args.exe.read_bytes()
    pe = parse_pe(data)
    print(f"image base 0x{pe['image_base']:X}")
    for sec in pe["sections"]:
        print(f"  {sec['name']:10s} vaddr 0x{sec['vaddr']:08X} vsize 0x{sec['vsize']:08X} "
              f"raw 0x{sec['raw']:08X} rawsize 0x{sec['rawsize']:08X}")
    targets = find_strings(data, pe, anchors)
    print(f"anchors located in file: {len(targets)}")
    for va, text in sorted(targets.items()):
        print(f"  0x{va:011X}  {text}")
    hits = scan(data, pe, targets)
    lines = []
    for va, op, text in sorted(hits):
        foff = va_to_file(va, pe)
        lines.append(f"0x{va:011X}  file 0x{foff:08X}  {op} -> {text}")
    print(f"\nxrefs: {len(hits)}")
    for line in lines:
        print("  " + line)
    if args.out:
        args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
