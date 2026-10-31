# Asset names and the plot-flag GUID problem

## Names are shipped in plaintext

The `.sb` (superbundle) files carry DbObject records with readable field names:

```
name \0 <len> <path>   sha1 \0 <20 bytes>   size \0 ...   originalSize \0 ...
```

Example (`Patch/Win32/galaxysystemcontent.sb` @0xB25):
`game/plots/levels/hubs/hub_tempest/plotexpressions/crit_tempest_0725_meridian_returntocity_available`

`tools/sb_names.py` extracts them by scanning printable runs and trimming back to the path
root. Counts on this install:

| Root | unique names | plot-looking (`/plots/`, `plotflag`) |
| --- | --- | --- |
| `Patch` | 240,299 | 1,148 |
| `Data` | 234,332 | 1,132 |
| union | — | **1,153** |

Plot names look like real flags, e.g.:

```
game/plots/levels/hubs/hub_nexus/contagion_trail01_visible
game/plots/bstory/coloniallife/increment_trackerfound
game/plots/levels/unc/eos_outpost_satellite_enabled
game/plots/levels/crit/m5_5_interlude/scourge_01_questmarkervisible
game/plots/levels/crit/m5_5_interlude/scourge_02_questmarkervisible
game/plots/levels/crit/m5_5_interlude/scourge_04_questmarkervisible
game/plots/levels/unc/storm/addup_allsitesinvestigated
```

This is the start of a human-readable check catalogue: quest steps, outpost/satellite
states, "visible" markers, counters.

## The GUID join is **not** a hash of the name

The save stores plot flags as 16-byte GUIDs (74,659 bools + 3,326 ints + 250 floats).
If the GUID were derived from the asset name we could name every flag offline. It is not.
`tools/probe_flag_hash.py` tested 1,153 names against the save's 78,235 GUIDs with:

- `md5(name)`, `md5(name)` byte-reversed, `sha1(name)[:16]`, `sha256(name)[:16]`
- the first 4 raw GUID bytes against DJB2-XOR, FNV-1a and CRC-32 of the name

**0 hits.** So the GUIDs are genuine asset identifiers stored in the game's data.

## Where the named flags actually come from (four sweeps)

Every asset family was swept for `PlotFlagId` references; the yield is very uneven:

| sweep | assets | parsed | with flags | distinct flags | **save keys** |
| --- | --- | --- | --- | --- | --- |
| `game/plots/` | 1,153 | 1,153 | 1,132 | 1,352 | 1,042 |
| levels + journals + space + prefabs + storyteller | 29,834 | 23,783 | 3,950 | 4,169 | 3,258 |
| `game/conversations/` | 100,279 | 31,129 | 2,613 | 10,688 | 4,700 |
| characters + items + weapons + ui + environments + ai | 65,513 | 62,693 | 1,589 | 358 | **320** |

The last sweep added **zero** new checks after quality filtering — its 320 flags were already
covered by better sources. So the productive families are plots, journals, space/storyteller and
conversations; the rest of the game's assets do not reference plot state.

Merged: **5,728 checks** (7.32% of the 78,235 plot flags a finished save contains). The
remaining ~72,500 flags are referenced by no swept asset.


## Consequence: cas reading was required for the join (solved)

`sb` entries only carry `name`, `sha1`, `size`, `originalSize` — no GUID. The GUID lives
inside the asset, so the pipeline is:

1. `layout.toc` → superbundles → `.toc`/`.sb` entry tables (name, sha1, size)
2. `cas.cat` catalogs → resolve each sha1 to (cas file, offset, size)
3. decompress the cas block (Oodle / zstd — the game data is compressed; a raw scan of six
   cas chunks for `game/plots/` found **0** plaintext hits, which confirms compression)
4. parse the partition (EBX) and read its GUID field and references

Gibbed's `Gibbed.Frostbite3.Unbundling` (`DataManager.cs`, `CompressionHelper.cs`,
`CasEncryptHelper.cs`) and `Gibbed.Frostbite3.ResourceFormats` (`PartitionFile.cs`,
`Partition/`) are the reference implementation for steps 1–4, and
`Gibbed.Frostbite3.Dynamic/PartitionReader.cs` shows how to walk the result. Frosty's
`EbxAssetEntry` exposes a `Guid` field, which is the value that matches the save.

## What is already usable without the join

- **Check detection**: `tools/plotflags.py diff` reports flags flipping between two saves
  (1,899 false→true across the two playthroughs) — a working check engine keyed by GUID.
- **Delivery**: `tools/save_edit.py` flips bools and sets ints/floats with valid CRCs and
  identical file size, proven by a bit-exact re-encode.
- **Names**: 240k asset paths, of which the plot subset gives a readable vocabulary as soon
  as the GUIDs are resolvable.
