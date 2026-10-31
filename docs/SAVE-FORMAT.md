# MEA save format — verified findings

Evidence: three real saves supplied by the owner in
`%USERPROFILE%\Documents\BioWare\Mass Effect Andromeda\Save\`, examined with
`tools/profsave.py` (container + header + prologue) and `tools/scan_strings.py` (body).
Everything below marked **verified** reproduced from the bytes; anything else is an
inference and is labelled as such.

## Container — verified

```
"FBCHUNKS"                    8 bytes
u16                           version            (saw 1)
u32                           header_length      (includes its own 4-byte checksum)
u32                           data_length        (includes its own 4-byte checksum)
u32                           header_checksum
header_length - 4 bytes       header block
u32                           data_checksum
data_length   - 4 bytes       data block
```

Checksum is the standard reflected CRC-32 (polynomial 0xEDB88320) seeded with
`0x12345678`, i.e. `zlib.crc32(block, 0x12345678)`. **Both checksums verified OK** on
`Career870ee94-1ManualSave`; the two `Careered8233e3-*` saves also pass the container
stage.

Small file `Career870ee94-1ManualSave`: 2,102,382 bytes, header 463, data 2,101,901.
Checksums are per-block, so editing a save means recomputing both.

## Header block — verified

```
"FBHEADER"                   8 bytes
u16                          version (1)
u32                          entry_count (19, fixed)
entry_count x { u32 hash, u16 length, bytes }    all little endian
```

The 19 entries are a fixed ordered table (name order from the enum below is *not* the
on-disk order; the hashes are what identify a field):

| # | hash | value in the 99.5% save | meaning |
| --- | --- | --- | --- |
| 0 | 0x18090FED | `14807` | game build/version string |
| 1 | 0xB73FFE0C | `SavedGame_HUB_Tempest` | area name string id |
| 2 | 0x0346EAF1 | `110` | game version (1.10) |
| 3 | 0x4D86FB47 | `216468;216467` | required DLC ids (`;` separated) |
| 4 | 0xC8E7F2D2 | `streaminginstall/...` | required install groups (`;` separated) |
| 5 | 0x6340D6A9 | `Sara` | profile name |
| 6 | 0x5261103A | `Sara (1)` | profile unique name |
| 7 | 0x12A98E23 | `141618836` | profile id |
| 8 | 0x574D2D1E | `Game/Levels/Hubs/Tempest/Tempest` | level id |
| 9 | 0xF5339720 | `132` | player level |
| 10 | 0x3E8C1126 | `true` | game completed |
| 11 | 0xCAE59484 | `false` | trial mode |
| 12 | 0x53DE4F39 | `99.53658` | completion percentage |
| 13 | 0xC163A5E4 | `212373801737` | date/time |
| 14 | 0x31B2A7DE | `88682` | level title id |
| 15 | 0x8587FF46 | `201922` | level floor id |
| 16 | 0x17D7B226 | `0` | level region id |
| 17 | 0x30E1A056 | `431843.7` | total playtime (seconds) |
| 18 | 0xA07DC1EE | `0` | name override string id |

All values are ASCII strings, even numeric ones.

## Data block — bit stream, verified to the body

The data block is **not byte aligned**. It is an MSB-first bit stream in which
multi-byte integers are stored little-endian and must be byte-swapped on read. Strings
are `u16 length` + that many 8-bit characters. Layout verified on the 99.5% save:

| offset (bits) | field |
| --- | --- |
| 0 | `"FB\0SAVE\n"` (8 bytes) |
| 64 | 4-bit flag (read as 1) |
| 68 | 27 bits skipped when the flag is set |
| 95 | u32 (see open question 3) |
| 127 | string: save name (`Career870ee94-1ManualSave`) |
| — | u16 game_version (3) |
| — | u16 save_version (22) |
| — | u16 unknown (10) |
| — | u16 unknown (0) |
| — | u32 user build info (9128063) |
| — | string: level name (`Game/Levels/RootLevel/RootLevel`) |
| — | u32 level unknown (0) |
| 735 | u16 bundle count (26) |
| 751 | 26 x { u16 length, bytes } preloaded bundle paths |
| **14111** | **body starts here** (byte 1763, 7 bits into a byte) |

Because every string length is a multiple of 8 bits, the stream keeps a constant
phase of 7 bits for the whole prologue.

### Bundle-length quirk

The first entry's length reads as `183` but the path is 55 characters; `183 & 0x7F` is
55. Every later entry reads as its true length. So the top bit of that field is a flag,
not part of the length. `profsave.py` masks it only when the unmasked value would not
be printable, which keeps the walk working without assuming all paths are < 128 bytes.

## Body — **solved** (2026-10-30, tools/profsave3.py)

The whole data block parses. `tools/profsave3.py` reads all three saves end to end and
**consumes every bit** (A: 16,815,176 / 16,815,176; the older saves leave 2 bits, which
matches the reference reader ignoring the final partial byte).

The decisive correction was the bit order: the stream is **LSB-first within each byte**.
Reading 16/32-bit values at a byte-aligned position therefore yields the little-endian
integer directly; my earlier MSB-first + byte-swap model only coincides at phase 0, which
is why the prologue kept disagreeing with the reference. Once corrected, the reference
field widths are right:

| field | width |
| --- | --- |
| magic `FB\0SAVE\n` | 64 bits |
| has-extra flag | 1 bit, then 27-bit int if set |
| timestamp | **u64**; subtract `210866803200` for Unix seconds (A = 2017-10-03T02:42:17Z) |
| save file name | string |
| game version / save version / 10 / 0 | u16 x4 (validated: 3 / 22 / 10 / 0) |
| user build info | u32 |
| level name | string |
| bundle count + names | u16 + strings (A: **154** bundles) |
| layer-inclusion dictionary | u16 count, each framed `{string, string}` (A: 2) |
| bundle heaps | u16(12) count, each 24-bit framed record (A: **84**) |
| unknown records | u16(12) count, each 24-bit framed `{u16,u16,u8}` |
| level hash | 16 bytes |
| unknown5 | u32(20); non-zero means an unsupported variant |
| unknown3 / unknown4 / bool | u16, u16 if unknown3 >= 5, 1 bit |
| component-data position | 26-bit position frame + u32(26) |
| entity bulk | u32 length, then that many bits |
| save name block | 24-bit frames: `{unknown6, unknown7, saveName}`, u32, guid, u32 |
| agent offsets | u8(4) count, each `{u8 index, u32(26) x5}` |
| entity table | 24-bit frame: `{u32 id, bool [+u32(26)], bool [+u32(26)]}`, then u32 lists |
| agent table | 24-bit frame: u8(4) count, each `{u32 nameHash, u8 index, u16 version}` (A: **13**) |
| component agents | 32-bit frame: u16 count, each 24-bit framed `{u32 hash, u16 version, body}` |

Frames are *validated* by the reference reader (end must equal the stated length), and our
port does the same, so a wrong assumption throws instead of silently desynchronising.

### Agent payloads

Each agent has five optional payload slots, referenced by absolute bit offsets in the
agent bulk data. A slot starts with a 24-bit length, then the payload. A: 13 agents, of
which idx 0 uses slot 0, idx 11/12 use slot 4, idx 10/7/9/8 use slot 3, idx 7 also uses
slot 2, and the rest use slot 1.

### The plot block — **solved**

Agent **idx 6** (`nameHash 0x96804D74`) is `PlotSaveGameAgent`; its slot-1 payload is the
plot state. Two nested 24-bit frames, then:

```
u16 version (4 on these saves)
string  "BioMetrics_PlotStartMarker"
u32(31) falseCount, then falseCount x 16-byte GUID      (version>=4 uses 31-bit counts)
u32(31) trueCount,  then trueCount  x 16-byte GUID
u16 intCount,       then intCount   x (GUID, i32)
u16 floatCount,     then floatCount x (GUID, f32)
u16 transformCount, then transformCount x (GUID, 12 x f32)   # Right/Up/Forward/Translate
u16 unknownCount,   then unknownCount x 24-bit framed (u32, GUID)
```

Measured on the three saves:

| save | bools | true | ints | floats | transforms |
| --- | --- | --- | --- | --- | --- |
| `Career870ee94-1ManualSave` (99.5%, 2017-10-03) | 74,659 | 35,836 | 3,326 | 250 | 133 |
| `Careered8233e3-0ManualSave` (older patch) | 66,973 | 35,395 | 3,034 | 252 | 133 |
| `Careered8233e3-2ManualSave` (same career, later save) | 66,973 | 35,395 | 3,034 | 252 | 133 |

`tools/plotflags.py diff` already reports observed transitions between two saves (1,899
flags false→true, 3,696 true→false, 1,029 ints changed between the two careers), which is
the mechanism the client will use to detect checks.

### Agent names are DJB2-XOR hashes

The 32-bit agent name hashes are **DJB2 with XOR** (`h = 5381; h = h*33 ^ byte`), verified:
`"PlotSaveGameAgent"` → `0x96804D74`. Confirmed so far: idx 6 PlotSaveGameAgent,
idx 3 EventTracker, idx 11 DestructionManager, idx 8 WorldMapSaveGameAgent,
idx 10 CodexListManagerSaveGameAgent, idx 0 WorldStateManager. The remaining seven need
name candidates from the game's own type list.

### Writing flags — **working** (tools/save_edit.py)

The plot region is `[u24 L0][u24 A][u24 B][body]` with frame lengths that *exclude* their
own header: `B = len(body)`, `A = 24 + B`, `L0 = 24 + A` (region total 72 bits + body).

`tools/save_edit.py verify` re-encodes an untouched plot block and compares it bit for bit
with the original: **round-trip identical** (10,197,046 bits) on the 99.5% save. That is
the proof the encoder matches the engine's layout, including list order.

Because an edit does not change the block's bit length (int/float values are fixed width,
and moving a bool between the false/true lists trades 128 bits for 128 bits), the region can
be spliced in place: same file size, everything else untouched, both CRC-32s recomputed.

Verified edits, each re-parsed with `profsave3` afterwards:

| edit | result |
| --- | --- |
| `set-int 005a705d-…-da665f9c03e6 7` | int went 3 → 7, size unchanged (2,102,382), header+data CRC ok, full parse ok |
| `set-bool 000c7931-…-0a1e3554019b false` | flag true → false, `trueCount` 35,836 → 35,835, CRCs ok |

Still unproven: **the game accepting an edited save**. That needs one load test in-game.

## Open questions

1. **Flag GUID → human name.** Plot flags are 16-byte GUIDs; the readable names live in
   the game's data. The executable contains `PlotFlagIds`, `PlotFlagsDefaultValues`,
   `NewGamePlusPlotFlags`, `PlotFlagDebugSymbol` and friends (see `docs/RE-TOOLING.md`),
   which are the likely tables for that mapping.
2. **In-game acceptance of an edited save** (above).
3. **The two `Careered8233e3` saves are byte-identical in plot terms**, so cross-career
   diffs are the only comparison we have. A fresh save from the current patch would help.

### Galaxy data agent (idx 4) — decoded

`GalaxyDataStateManagerSaveAgent` (name hash `0x066D83C3`), version 2:

```
u24 frame {
    u24 frame { guid current_system; guid current_destination }
    Unknown3: u24 frame { u32 count, [guid,u32]*; u32 count, [guid,u32]* }
    Unknown4: same
}
```

On the 99.5% save it is only 480 bits of payload — current system/destination and **both
key/value maps empty** (`tools/probe_galaxy.py`). So "which planets are unlocked" is not
stored here in these saves.

### Where planet unlocks are **not** (three hypotheses ruled out)

1. **Plot flags.** `game/plots/systems/space/galaxymap_unlock_*` (defaultsystems, postayahub,
   postayavault, postkadara, postm4, postm5, postmcm, remnantcity, kettflagship, meridian)
   are `PlotAction` entities; every flag they reference is **false in the 99.5% save**. They
   are transient triggers, not persistent state.
2. **`DestinationData` assets** (410 under `game/space/destinations/`). Fields are
   `CurrentDestinationFlag`, `IncludeInCompletion`, `ExcludeFromJournalTask`, `ScannedFlag`,
   `Anomalies[]` — no "unlocked" flag.
3. **GalaxyDataStateManagerSaveAgent** — see above.

### Next lead: an early save

Both supplied saves are **finished playthroughs** — 99.5% and 87.4% completion, level 132,
`game completed = true` — so diffing them surfaces choice differences, not progression. An
early or mid-game save is needed to find the planet-access and Meridian-completion flags.
`tools/flag_diff.py` is ready for it (on the current pair: 5,595 bool changes of which 18 are
named, 1,029 int changes of which 113 are named).

### Item delivery: two hypotheses ruled out

- **Weapons are not addressable through research-project flags.** Every weapon research project
  asset (`game/items/research/projects/weapons/.../researchproject_weapon_<class>_<name>`) carries
  the *same* `MECraftingResearchProjectItemData.CompletedFlag` (`25274046-…`) and the same
  `BoolProvider_PlotCondition` flag (`41cc328c-…`) — verified across 51 weapon projects
  (`tools/probe_weapon_flags.py`). Per-project state lives in the crafting progression data, not
  in plot flags, so a weapon cannot be granted by setting a flag.
- **No named win flag.** Scoring all 172 Meridian/finale/completion candidates against both
  finished saves (`tools/find_goal_flag.py`) found only cinematic perf flags and landing markers;
  none is a campaign-complete flag.

Consequence: item delivery needs the player's crafting/inventory data, which lives in the
component-container section of the save that is not decoded (Gibbed implements only the
customization component). The **mechanism** is built and tested (`tools/apply_effects.py`): apply
N flag writes in one rewrite, back up the input, verify only the requested flags changed and the
size is unchanged. Only the item → flag table is missing.

### Batch delivery — verified

```
bool 3f530000-…: False -> True
bool 34c10000-…: False -> True
int  768b1600-…: 0 -> 7
verified 3 changed flag(s), size unchanged, CRCs recomputed
SELFTEST PASSED
```

## Test data quality

`Career870ee94-1ManualSave` is a **99.5% complete** save (level 132, game completed,
120 hours) — the oracle for "what a finished campaign sets". The `Careered8233e3` saves are
an older patch and give a second playthrough for cross-career diffs.
