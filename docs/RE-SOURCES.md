# RE reference sources

Collected while solving the Frostbyte container/EBX problem. Each entry says what it is
actually good for, so nobody re-reads them from scratch.

## Used and verified

| Source | What it gave us |
| --- | --- |
| [gibbed/Gibbed.MassEffectAndromeda](https://github.com/gibbed/Gibbed.MassEffectAndromeda) | The save format: `SaveFormats/SaveFile.cs`, `SaveData.cs` (frame/agent grammar), `Data/Plot.cs` (GUID-keyed plot block), `FileFormats/BitReader.cs` (the LSB-first bit reader that cracked the prologue), `Hashing/DJB.cs` (matches the agent name hashes). Our parser and writer are ports of these. |
| [FrostyToolsuite](https://github.com/FrostyToolsuite/FrostyToolsuite) | MEA profile constants (`FrostyCli/Profiles/Mea.json`: DataVersion 20170320, FrostbiteVersion 2015.4.6, EbxVersion 2) and the runtime `AssetManager`/`EbxAssetEntry` model (`Guid` + `Name`). Frosty 1.0.6.3 binaries are on disk and loadable from bytes. |

## New references from the owner (2026-10-30)

### GreyDynamics/Frostbite3_Editor — Java, discontinued, but documents the formats

Repo: https://github.com/GreyDynamics/Frostbite3_Editor (default branch `develop`)

- `__DOCUMENTATION__/ebx/ebx.txt` — **the most useful document we have for EBX**:
  - magic `0x0fb2d1ce` ("fb2", still used in Frostbite 3), stored as `CE D1 B2 0F` in
    little-endian files
  - full classic header layout (string-section offset/length, instance repeaters, complex
    and field counts, keyword/string/array/payload sizes, 16-byte **file GUID**, padding)
  - instance repeaters are two `u16`s; only the first *N* instances carry a GUID
  - instance alignment rules (align before reading a GUID; alignment=4 quirk subtracts 8)
  - field type notes: `0x407d`/`0x409d` strings with signed length (-1 = empty)
- `__DOCUMENTATION__/compression/lz4.txt` — compression notes
- `__DOCUMENTATION__/patch_system/Delta Patch system.txt` — delta patch layout
- sample raw EBX files under `__DOCUMENTATION__/ebx/sample_ebx/` — a test corpus
- `binary_build.jar` — runnable editor, useful to compare behaviour

Why it matters: the **file GUID in the EBX header** is a strong candidate for the
16-byte identifiers the save stores as plot flags. If a plot asset's EBX header GUID
matches a save GUID, we have the join.

### CallumCVM/FrostbiteGen — C++, generates a full Frostbite 3 SDK

Repo: https://github.com/CallumCVM/FrostbiteGen

Small project (`classinfo.cpp`, `main.cpp`, `structs.h`) that walks instance/field
descriptors to emit a complete class description for a Frostbite 3 game. Tested by its
author on BF4 and Star Wars Battlefront, not MEA, so treat it as a structural reference
rather than a working MEA tool.

### FMTDev/FMT.Releases — binaries only

Repo: https://github.com/FMTDev/FMT.Releases — "Frosty Mod Tools" releases: a mod tool for
Frostbite games that can deploy to multiple platforms. No source. Potentially relevant when
we build our own mod manager (mod packaging/deployment), not for the data join.

## Not useful / dead ends (recorded so they are not repeated)

- Save GUIDs do not appear in any `.toc`/`.sb` metadata (1 GB scanned, 0 hits).
- Save GUIDs are not hashes of asset names (md5/sha1/sha256 prefixes, djb2/fnv/crc32).
- `MassEffectAndromeda.exe` has no code references to its own plot/save class names — they
  are RTTI-only; the magics are immediates.
