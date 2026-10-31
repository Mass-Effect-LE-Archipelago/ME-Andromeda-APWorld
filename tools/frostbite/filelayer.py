"""Frostbite "file layers": the obfuscation/signature wrappers around metadata.

Three layers are documented in Gibbed's ``Gibbed.Frostbite3.VfsFormats/FileLayers``
and two of them were observed in the real Mass Effect Andromeda install:

Ooa obfuscation
    ``.toc`` and ``layout.toc`` files.  The last 36 bytes are::

        int32  setupLength        (little-endian)
        byte[32] "@e!adnXd$^!rfOsrDyIrI!xVgHeA!6Vc"

    The *ciphertext* for the real header is those last ``setupLength`` bytes,
    run through a DICE "bogocrypt" routine.  The decrypted 465-byte setup
    block then tells us the plaintext size (u32 @ 402) and a one-byte mode
    (``setup[4]``): mode 2 XOR-decrypts the body with a rolling key seeded from
    ``setup[5]``, mode 3 stores the body in the clear, mode 1 is unimplemented
    in Gibbed as well.

DiCE obfuscation / signature
    Alternative wrappers keyed by the magics ``0x00CED100`` (obfuscated) and
    ``0x01CED100`` (signed).  Neither magic occurs in this install; both are
    implemented anyway so the reader fails cleanly rather than misparsing.

Everything else (``.sb``) is stored with no layer at all, which is why the
``.sb`` files start directly with a DbObject tag byte.
"""
from __future__ import annotations

import struct

__all__ = [
    "FileLayerError",
    "OOA_SIGNATURE",
    "dice_is_obfuscated",
    "dice_deobfuscate",
    "dice_is_signed",
    "dice_skip_signature",
    "ooa_is_obfuscated",
    "ooa_deobfuscate",
    "strip",
]

OOA_SIGNATURE = b"@e!adnXd$^!rfOsrDyIrI!xVgHeA!6Vc"  # 32 bytes
OOA_TAIL_SIZE = 36  # int32 setupLength + 32 byte signature

DICE_SIGNATURE = 0x01CED100
DICE_OBFUSCATED_SIGNATURE = 0x00CED100

_MASK = 0xFFFFFFFF


class FileLayerError(Exception):
    """Raised when a file layer cannot be recognised or decoded."""


# ---------------------------------------------------------------------------
# DiCE layers
# ---------------------------------------------------------------------------
def dice_is_obfuscated(data: bytes) -> bool:
    return len(data) >= 8 and struct.unpack_from("<I", data, 0)[0] == DICE_OBFUSCATED_SIGNATURE


def dice_is_signed(data: bytes) -> bool:
    return len(data) >= 8 and struct.unpack_from("<I", data, 0)[0] == DICE_SIGNATURE


def dice_deobfuscate(data: bytes) -> bytes:
    if not dice_is_obfuscated(data):
        raise FileLayerError("not DiCE-obfuscated")
    if struct.unpack_from("<I", data, 4)[0] != 0:
        raise FileLayerError("DiCE obfuscation: second dword is not zero")
    pos = 8 + 288
    key = data[pos:pos + 257]
    if len(key) != 257:
        raise FileLayerError("DiCE obfuscation: truncated key")
    padding = data[pos + 257:pos + 260]
    if padding != b"\x00\x00\x00":
        raise FileLayerError("DiCE obfuscation: non-zero padding")
    body = bytearray(data[pos + 260:])
    klen = len(key)
    for i in range(len(body)):
        body[i] ^= key[i % klen]
        body[i] ^= 0x7B
    return bytes(body)


def dice_skip_signature(data: bytes) -> bytes:
    if not dice_is_signed(data):
        raise FileLayerError("not DiCE-signed")
    if struct.unpack_from("<I", data, 4)[0] != 0:
        raise FileLayerError("DiCE signature: second dword is not zero")
    return data[8 + 548:]


# ---------------------------------------------------------------------------
# Ooa layer
# ---------------------------------------------------------------------------
def ooa_is_obfuscated(data: bytes) -> bool:
    if len(data) < OOA_TAIL_SIZE:
        return False
    return data[-32:] == OOA_SIGNATURE


def _rotl(value: int, count: int) -> int:
    count &= 31
    value &= _MASK
    if count == 0:
        return value
    return ((value << count) | (value >> (32 - count))) & _MASK


def _crypt_section(buf: bytearray, offset: int, count: int, seed: int) -> None:
    """Gibbed: OoaObfuscationLayer.Bogocrypt.CryptSection."""
    h = seed & _MASK
    j = 0
    for i in range(count):
        o = offset + i
        b = (buf[o] ^ ((h & 0xFF) + ((h >> 8) & 0xFF) + ((h >> 16) & 0xFF) + ((h >> 24) & 0xFF))) & 0xFF
        buf[o] = b
        c = _rotl(h, b & 31)
        t = (b | ((b | ((b | (b << 8)) << 8)) << 8)) & _MASK
        h = _rotl((t + c) & _MASK, 1)
        if j > 16:
            h = (h * 2) & _MASK
            j = 0
        j += 1


def _bogocrypt(buf: bytearray) -> None:
    """Gibbed: OoaObfuscationLayer.Bogocrypt.Crypt (in-place)."""
    length = len(buf)
    if length < 410:
        raise FileLayerError(f"Ooa setup block too small ({length} bytes)")

    length1 = struct.unpack_from("<H", buf, 392)[0]

    a = 0
    o = 410
    for _ in range(length1):
        if o >= length:
            raise FileLayerError("Ooa setup block: cipher stream runs past end")
        a = (buf[o] ^ (2 * (buf[o] + a))) & _MASK
        o += 1

    b = (
        (buf[405] ^ (2 * (buf[405] + (
            buf[404] ^ (2 * (buf[404] + (
                buf[403] ^ (2 * (buf[403] + (
                    buf[402] ^ (2 * buf[402])))))))))))
        + (buf[3] ^ (2 * (buf[3] + (
            buf[2] ^ (2 * (buf[2] + (
                buf[1] ^ (2 * (buf[1] + (
                    buf[0] ^ (2 * buf[0])))))))))))
        + (buf[391] ^ (2 * buf[391]))
        + a
        + (buf[397] ^ (2 * (buf[397] + (
            buf[396] ^ (2 * (buf[396] + (
                buf[395] ^ (2 * (buf[395] + (
                    buf[394] ^ (2 * buf[394])))))))))))
    ) & _MASK

    c = (
        (buf[409] ^ (2 * (buf[409] + (
            buf[408] ^ (2 * (buf[408] + (
                buf[407] ^ (2 * (buf[407] + (
                    buf[406] ^ (2 * buf[406])))))))))))
        + b
    ) & _MASK

    d = 0
    o = 4
    for _ in range(129):
        j = buf[o]
        k = buf[o + 1]
        l = buf[o + 2]
        d = (l ^ (2 * (l + (k ^ (2 * (k + (j ^ (2 * (j + d))))))))) & _MASK
        o += 3

    length2 = struct.unpack_from("<H", buf, 392)[0]
    if length2:
        _crypt_section(buf, 410, length2, 0x45EA1278)

    buf[391] ^= 0xB9
    _crypt_section(buf, 394, 4, 0x45EA1278)
    _crypt_section(buf, 0, 4, 0x45EA1278)
    _crypt_section(buf, 402, 4, 0x45EA1278)
    _crypt_section(buf, 406, 4, 0x45EA1278)
    _crypt_section(buf, 4, 387, 0x45EA1278)
    struct.pack_into("<I", buf, 398, length)

    # the seed byte is tweaked last, based on a value that only exists after the
    # sections above have been decrypted
    e = (d + c) & 0xFF
    if struct.unpack_from("<H", buf, 325)[0] in (1, 2, 4, 8):
        buf[5] ^= e


def ooa_setup(data: bytes) -> dict:
    """Decrypt and describe the Ooa setup block without touching the body."""
    if not ooa_is_obfuscated(data):
        raise FileLayerError("no Ooa signature in the last 36 bytes")
    tail = data[-OOA_TAIL_SIZE:]
    setup_length = struct.unpack_from("<i", tail, 0)[0]
    if setup_length <= 0 or setup_length > len(data):
        raise FileLayerError(f"Ooa setup length {setup_length} is out of range")
    setup = bytearray(data[len(data) - setup_length:])
    _bogocrypt(setup)
    version = struct.unpack_from("<I", setup, 0)[0]
    mode = setup[4]
    file_size = struct.unpack_from("<I", setup, 402)[0]
    return {
        "setup_length": setup_length,
        "version": version,
        "mode": mode,
        "seed": setup[5],
        "file_size": file_size,
        "tail_size": len(data) - file_size,
        "setup": bytes(setup),
    }


def ooa_deobfuscate(data: bytes) -> bytes:
    info = ooa_setup(data)
    version = info["version"]
    mode = info["mode"]
    file_size = info["file_size"]
    if version > 4:
        raise FileLayerError(f"unsupported Ooa version {version}")
    if file_size > len(data):
        raise FileLayerError("Ooa plaintext size exceeds file size")
    if mode == 3:
        return data[:file_size]
    if mode == 2:
        seed = info["seed"]
        body = bytearray(data[:file_size])
        magic = seed
        for i in range(file_size):
            b = body[i]
            body[i] = b ^ magic
            magic = ((b ^ seed) - i) & 0xFF
        return bytes(body)
    if mode == 1:
        raise FileLayerError("Ooa mode 1 is not supported (unimplemented upstream too)")
    raise FileLayerError(f"unknown Ooa mode {mode}")


# ---------------------------------------------------------------------------
def layers_of(data: bytes) -> list[str]:
    """Names of every layer that appears to wrap ``data``."""
    names = []
    if ooa_is_obfuscated(data):
        names.append("ooa")
    if dice_is_obfuscated(data):
        names.append("dice-obfuscation")
    elif dice_is_signed(data):
        names.append("dice-signature")
    return names


def strip(data: bytes, verbose: bool = False):
    """Remove every known file layer.  Returns ``(payload, layer_names)``."""
    names = layers_of(data)
    if ooa_is_obfuscated(data):
        data = ooa_deobfuscate(data)
    if dice_is_obfuscated(data):
        data = dice_deobfuscate(data)
    elif dice_is_signed(data):
        data = dice_skip_signature(data)
    return data, names
