"""Edit MEA plot flags by re-encoding the plot agent block in place.

The plot block is a bit region inside the save's data block:

    [u24 L0][u24 A][u24 B][body...]        A = 24 + B,  B = 24 + len(body),  L0 = 24 + A

Editing a flag's *value* (int, float) or moving a bool between the true/false lists does
not change how many bits the block needs, so the region is rewritten in place. Inserting an
absent bool grows the block by 128 bits; everything after it moves, so the absolute positions
recorded by profsave3 (`data["fixups"]`) and the container's data length are patched. The
region need not be byte aligned. Both CRC-32s are recomputed afterwards.

`verify` re-encodes an untouched save and compares the region with the original bytes:
that is the proof the encoder reproduces the engine's layout exactly.

Usage:
  python save_edit.py verify    <save>
  python save_edit.py set-int   <save> <guid> <value> <out>
  python save_edit.py set-float <save> <guid> <value> <out>
  python save_edit.py set-bool  <save> <guid> <true|false> <out>
"""
from __future__ import annotations

import argparse
import binascii
import struct
import sys
from pathlib import Path

import profsave3 as p

CRC_SEED = 0x12345678


def guid_raw(text: str) -> bytes:
    """GUID text -> the 16 bytes as stored in the save (.NET order)."""
    parts = text.split("-")
    if len(parts) != 5:
        raise ValueError(f"bad guid {text!r}")
    raw = (bytes.fromhex(parts[0])[::-1] + bytes.fromhex(parts[1])[::-1]
           + bytes.fromhex(parts[2])[::-1] + bytes.fromhex(parts[3]) + bytes.fromhex(parts[4]))
    if len(raw) != 16:
        raise ValueError(f"bad guid {text!r}")
    return raw


class BitWriter:
    """LSB-first bit writer matching the engine's reader."""

    def __init__(self) -> None:
        self.buf = bytearray()
        self.bit = 0

    def write(self, value: int, nbits: int) -> None:
        if nbits < 0:
            raise ValueError("negative bit count")
        remaining = nbits
        shift = 0
        while remaining > 0:
            offset = self.bit % 8
            left = min(8 - offset, remaining)
            mask = (1 << left) - 1
            if self.bit >> 3 >= len(self.buf):
                self.buf.append(0)
            chunk = (value >> shift) & mask
            self.buf[self.bit >> 3] |= (chunk << offset) & 0xFF
            remaining -= left
            shift += left
            self.bit += left

    def bytes_(self, raw: bytes) -> None:
        for b in raw:
            self.write(b, 8)

    def guid(self, text: str) -> None:
        self.bytes_(guid_raw(text))

    def string(self, text: str) -> None:
        raw = text.encode("utf-8")
        self.write(len(raw), 16)
        self.bytes_(raw)

    def value(self) -> bytes:
        return bytes(self.buf)


def encode_body(plot: dict) -> tuple[bytes, int]:
    """Encode the plot payload after the two frame headers."""
    w = BitWriter()
    version = plot["version"]
    w.write(version, 16)
    if version >= 2:
        w.string(plot["marker"])
    nbits = 31 if version >= 4 else 16
    bools = plot["bools"]
    # The game writes each list sorted by serialized GUID bytes; keep that for inserted/moved keys.
    true_keys = sorted((k for k, v in bools.items() if v), key=guid_raw)
    false_keys = sorted((k for k, v in bools.items() if not v), key=guid_raw)
    # TRUE list first (see profsave3.parse_plot).
    w.write(len(true_keys), nbits)
    for k in true_keys:
        w.guid(k)
    w.write(len(false_keys), nbits)
    for k in false_keys:
        w.guid(k)
    w.write(len(plot["ints"]), 16)
    for k, v in plot["ints"].items():
        w.guid(k)
        w.write(v & 0xFFFFFFFF, 32)
    w.write(len(plot["floats"]), 16)
    for k, v in plot["floats"].items():
        w.guid(k)
        w.write(struct.unpack("<I", struct.pack("<f", v))[0], 32)
    w.write(len(plot["transforms"]), 16)
    for k, vals in plot["transforms"].items():
        w.guid(k)
        for val in vals:
            w.write(struct.unpack("<I", struct.pack("<f", val))[0], 32)
    if version >= 3:
        w.write(len(plot["unknown"]), 16)
        for k, v in plot["unknown"].items():
            w.write(16 + 128, 24)  # u32 key + guid payload
            w.write(k, 32)
            w.guid(v)
    return w.buf, w.bit


def region(data_block: bytes, save) -> tuple[int, int, int]:
    """Return (start_bit, end_bit, body_start_bit) of the plot agent payload."""
    for agent in save.agents:
        off = agent.offsets[1]
        if not off:
            continue
        r = p.BitReader(data_block, off, len(data_block) * 8 - off)
        length0 = r.read(24)
        payload_start = r.pos
        head = p.BitReader(data_block, payload_start, min(length0, 1024)).bytes_(min(60, length0 // 8))
        if b"BioMetrics_PlotStartMarker" not in head:
            continue
        probe = p.BitReader(data_block, payload_start, length0)
        p.parse_plot(probe)
        return off, probe.pos, payload_start
    raise SystemExit("plot agent not found")


def encode_region(plot: dict) -> tuple[bytes, int]:
    body, body_bits = encode_body(plot)
    # Frame lengths exclude their own header (verified against a real save):
    #   B = len(body), A = 24 + B, L0 = 24 + A
    b_frame = body_bits
    a_frame = 24 + b_frame
    l0 = 24 + a_frame
    w = BitWriter()
    w.write(l0, 24)
    w.write(a_frame, 24)
    w.write(b_frame, 24)
    for i in range(body_bits):
        w.write((body[i >> 3] >> (i % 8)) & 1, 1)
    return w.buf, w.bit


def splice(data_block: bytes, start_bit: int, end_bit: int, new_buf: bytes, new_bits: int) -> bytearray:
    """Replace bits [start_bit, end_bit) with new_bits from new_buf (LSB-first, any alignment).

    Bits after the region move by new_bits - (end_bit - start_bit); the caller fixes any
    absolute positions that point past it. The block is padded to whole bytes with zeros.
    """
    total = len(data_block) * 8
    src = int.from_bytes(data_block, "little")
    region_val = int.from_bytes(new_buf, "little") & ((1 << new_bits) - 1)
    low = src & ((1 << start_bit) - 1)
    high = src >> end_bit
    out_bits = total - (end_bit - start_bit) + new_bits
    value = low | (region_val << start_bit) | (high << (start_bit + new_bits))
    return bytearray(value.to_bytes((out_bits + 7) // 8, "little"))


def _write_bits(block: bytearray, pos: int, nbits: int, value: int) -> None:
    for i in range(nbits):
        j = pos + i
        if (value >> i) & 1:
            block[j >> 3] |= 1 << (j & 7)
        else:
            block[j >> 3] &= ~(1 << (j & 7)) & 0xFF


def _apply_fixups(block: bytearray, save, region_end: int, delta: int) -> int:
    """Move absolute positions past the plot region by delta and grow the agent-bulk length.

    Done on the original block, before the splice: every fixup field lies outside the plot region
    and keeps its width, so the recorded positions are valid there; the splice then carries the
    fields after the region along with everything else. Returns fields patched.
    """
    patched = 0
    reader = p.BitReader(bytes(block), 0, len(block) * 8)
    for pos, nbits, kind in save.data["fixups"]:
        reader.pos = pos
        value = reader.read(nbits)
        if kind == "len":
            new = value + delta
        elif value >= region_end:
            new = value + delta
        else:
            continue
        if new >= 1 << nbits:
            raise SystemExit(f"fixup at bit {pos} overflows {nbits} bits")
        _write_bits(block, pos, nbits, new)
        patched += 1
    return patched


def rewrite(path: Path, out_path: Path, mutate) -> None:
    raw = path.read_bytes()
    header_block, data_block, info = p.unwrap(raw)
    if not (info["header_crc_ok"] and info["data_crc_ok"]):
        raise SystemExit("input CRCs are invalid; refusing to write")
    save = p.load(path)
    if not save.plot:
        raise SystemExit("no plot block found")
    start, end, _ = region(data_block, save)
    plot = {k: (dict(v) if isinstance(v, dict) else v) for k, v in save.plot.items()}
    mutate(plot)
    new_buf, new_bits = encode_region(plot)
    delta = new_bits - (end - start)
    if delta % 8:
        raise SystemExit(f"plot region grew by {delta} bits, not a whole number of bytes")
    if new_bits >= 1 << 24:
        raise SystemExit("plot region too large for its 24-bit frame")
    block = bytearray(data_block)
    patched = _apply_fixups(block, save, end, delta) if delta else 0
    edited = splice(block, start, end, new_buf, new_bits)
    if len(edited) != len(data_block) + delta // 8:
        raise SystemExit(f"data block {len(data_block)} -> {len(edited)} bytes, expected +{delta // 8}")

    header_len = info["header_length"]
    new_data_crc = binascii.crc32(bytes(edited), CRC_SEED) & 0xFFFFFFFF
    out = bytearray(raw[:18 + header_len])
    struct.pack_into("<I", out, 14, len(edited) + 4)  # container data length includes its CRC
    out += struct.pack("<I", new_data_crc)
    out += edited
    if len(out) != len(raw) + delta // 8:
        raise SystemExit(f"output length {len(out)} != input {len(raw)} + {delta // 8}")
    out_path.write_bytes(bytes(out))
    p.load(out_path)  # full re-parse: frames, agent offsets and component position must still line up
    extra = f", grew {delta // 8} bytes, {patched} position field(s) moved" if delta else ""
    print(f"wrote {out_path} ({len(out)} bytes, plot region bits {start}..{end}{extra})")


def apply_batch(save_path: Path, out_path: Path, ops: list[dict]) -> list[str]:
    """Apply several flag writes in one rewrite. Ops: {kind: bool|int|float, guid, value}.

    Returns a log. Unknown guids are reported and skipped rather than silently dropped.
    """
    log: list[str] = []

    def mutate(plot):
        for op in ops:
            kind, guid, value = op["kind"], op["guid"], op.get("value")
            if kind == "bool":
                # Absent bools are inserted: the save only lists flags the game has touched.
                was = plot["bools"].get(guid, "absent")
                log.append(f"bool {guid}: {was} -> {bool(value)}")
                plot["bools"][guid] = bool(value)
            elif kind == "int":
                if guid not in plot["ints"]:
                    log.append(f"SKIP int {guid}: not an int flag in this save")
                    continue
                log.append(f"int {guid}: {plot['ints'][guid]} -> {int(value)}")
                plot["ints"][guid] = int(value)
            elif kind == "float":
                if guid not in plot["floats"]:
                    log.append(f"SKIP float {guid}: not a float flag in this save")
                    continue
                log.append(f"float {guid}: {plot['floats'][guid]} -> {float(value)}")
                plot["floats"][guid] = float(value)
            else:
                log.append(f"SKIP unknown kind {kind!r}")

    rewrite(save_path, out_path, mutate)
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify")
    v.add_argument("save", type=Path)
    si = sub.add_parser("set-int")
    si.add_argument("save", type=Path)
    si.add_argument("guid")
    si.add_argument("value", type=int)
    si.add_argument("out", type=Path)
    sf = sub.add_parser("set-float")
    sf.add_argument("save", type=Path)
    sf.add_argument("guid")
    sf.add_argument("value", type=float)
    sf.add_argument("out", type=Path)
    sb = sub.add_parser("set-bool")
    sb.add_argument("save", type=Path)
    sb.add_argument("guid")
    sb.add_argument("value", choices=["true", "false"])
    sb.add_argument("out", type=Path)
    args = ap.parse_args()

    if args.cmd == "verify":
        raw = args.save.read_bytes()
        header_block, data_block, info = p.unwrap(raw)
        save = p.load(args.save)
        start, end, _ = region(data_block, save)
        new_buf, new_bits = encode_region(save.plot)
        old_bits = end - start
        print(f"region bits: original {start}..{end} ({old_bits}), re-encoded {new_bits}")
        if new_bits != old_bits:
            print("LENGTH MISMATCH")
            return 1
        same = True
        for i in range(new_bits):
            a = (data_block[(start + i) >> 3] >> ((start + i) % 8)) & 1
            b = (new_buf[i >> 3] >> (i % 8)) & 1
            if a != b:
                same = False
                print(f"first differing bit at region offset {i} (absolute {start + i})")
                break
        print("round-trip identical" if same else "round-trip DIFFERS")
        return 0 if same else 1

    if args.cmd == "set-int":
        def mutate(plot):
            if args.guid not in plot["ints"]:
                raise SystemExit(f"guid {args.guid} is not an int flag")
            print(f"int {args.guid}: {plot['ints'][args.guid]} -> {args.value}")
            plot["ints"][args.guid] = args.value
        rewrite(args.save, args.out, mutate)
    elif args.cmd == "set-float":
        def mutate(plot):
            if args.guid not in plot["floats"]:
                raise SystemExit(f"guid {args.guid} is not a float flag")
            print(f"float {args.guid}: {plot['floats'][args.guid]} -> {args.value}")
            plot["floats"][args.guid] = args.value
        rewrite(args.save, args.out, mutate)
    elif args.cmd == "set-bool":
        want = args.value == "true"

        def mutate(plot):
            bools = plot["bools"]
            if args.guid not in bools and (args.guid in plot["ints"] or args.guid in plot["floats"]):
                raise SystemExit(f"guid {args.guid} is not a bool flag")
            print(f"bool {args.guid}: {bools.get(args.guid, 'absent (inserted)')} -> {want}")
            bools[args.guid] = want
        rewrite(args.save, args.out, mutate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
