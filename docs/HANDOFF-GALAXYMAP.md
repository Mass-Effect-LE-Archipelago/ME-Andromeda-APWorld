# Galaxy-map gating — handoff (2026-10-31)

**Read this first if you are picking up the "planet/system gating" thread.** It is self-contained: the
goal, everything proven, the three experiments (two failed, one diagnostic), the engine semantics we
cracked, the open hypotheses with the cheapest discriminating test for each, and the tooling.

Project: `C:\Users\unowi\Documents\APWorldMaker\Mass Effect Andromeda APWorld`
Companion docs: `docs/GALAXYMAP-GATE.md` (detailed evidence), `docs/SYSTEM-NAMES.md` (system table),
`docs/HANDOFF.md` §7 (project-level status).

---

## 1. Immediate state / restore

The last in-game test (v2) left the galaxy map **empty** (no systems at all). The mod files have been
removed from the Frosty mods folder, but Frosty's applied overlay under
`C:\Steam\steamapps\common\Mass Effect Andromeda\ModData\Default\patch\` still holds the v2 chunks.

- **To play vanilla now:** launch from **Steam** (not Frosty). Frosty's overlay only loads through its
  own launcher.
- **To clear the overlay:** open Frosty with no AP mod present and Apply once. If the map is still
  empty after that, delete `ModData\Default\patch` and launch from Steam.
- Nothing was ever written to the game's own `Data\`/`Patch\` files — the overlay is the only side
  effect.

---

## 2. The goal

The AP world ships planet access as items, but in game the order is honour-system. The target is a
real in-game gate: start with one or two systems open, unlock the rest through items/checks. The
owner's build order has this as the last open item; the fallback (acceptable) is honour-system.

---

## 3. What is established (do not re-derive)

### 3.1 The galaxy map prefab

| | |
| --- | --- |
| asset | `game/ui/pausemenu/galaxymap/prefabs/spawnedgalaxymap` |
| partition GUID | `e9d830c0-8980-11e5-b9be-d95347869af1` |
| size | 32,512 B (also dumped as `tools/scratch/galaxymap.bin`) |
| listing | `Patch/Win32/game/levels/hubs/tempest/tempest.sb`, bundle `win32/game/levels/hubs/tempest/dsg_space` |

Structure: 94 instances — 42 `SpatialReferenceObjectData`, **38 `PlotConditionNotificationEntityData`**,
7 `EntityData`, 3 `GameObjectData`, 2 `SpatialEntityData`, 1 `PrefabBlueprint`, 1
`DynamicDataContainer`; 92 `Objects`, 243 property / 77 link / **116 event** connections, 46 imports.

Its 46 imports: **38 × `game/space/systems/systemdata/systemdata_<system>`**, plus
`galaxysystemlocatoruiprefab`, `galaxymapuichannel`, and 6 unresolved.

### 3.2 The per-system rows

`game/space/systems/systemdata/systemdata_<sys>` — 848 B (aya) / 864 B (rest), one `SystemData`
(base `GalaxyObjectData`):

```
Name, ObjectDisplayName {StringId}, ObjectCategory 5, AvailableFlag {PlotFlagId}, VisitedFlag {PlotFlagId},
SectorDisplayName, StarType, Icon {import}
```

38 systems total: aya_* 13, kadara_* 12, nexus_* 9, meridian_* 4.

### 3.3 Names and planets

Each system prefab imports `spaceobject_sun_<name>` (the in-game name) and `spaceobject_plt_*`
(planets). Full table in **`docs/SYSTEM-NAMES.md`**, e.g.:

| id | name | planets |
| --- | --- | --- |
| aya_01 | Onaon | Aya, Maeraav |
| aya_05 | Tafeno | Solad (+ Salarian ark) |
| kadara_01 | Gavorkam | Kadara |
| kadara_10 | Civki | — |
| meridian_01 | Saajor | Meridian hub, Roha |
| nexus_02 | Ibn Majid | Eos, Nyota Penda |

Caveat: the three map labels **Rohvir, Pytheas, Skeldah** match no sun asset (localized names of
systems whose internal names are placeholders `c11`/`c12`/…). The other 12 visible labels matched
exactly.

### 3.4 The flag chain

- The prefab's 38 watched flags **are exactly** the 38 `SystemData.AvailableFlag` values (set
  equality, `probe_galaxymap_prefab.py verify`).
- Ten `game/plots/systems/space/galaxymap_unlock_*` plot assets `PlotActionEntityData`-write 34 of the
  38 (defaultsystems, postayahub, postayavault, postkadara, postm4, postm5, postmcm, meridian,
  remnantcity, kettflagship). The remaining four (`aya_07`, `aya_12`, `nexus_03`, `nexus_07`) are
  referenced inside their own system prefab.
- **The flags are never true:** 0/38 in all 32 career saves on this machine, including the finished
  74k-flag one, where all 38 are present-but-false. They are absent entirely from a fresh M0 save.

### 3.5 The jump graph

80 `JumpToSystem` edges over 38 systems, 0 unresolved imports, every system has an inbound edge
(`probe_galaxymap_prefab.py jumpgraph`). Availability is the only missing piece; fuel/range is the
only other limiter.

---

## 4. The three experiments

### v1 — set every row's `AvailableFlag` to `alwaystrue` → **no effect**

Built `tools/build_galaxymap_mod.py` (38 rows, 78 bundles, one `modify` action per listing bundle).
Applied, game launched, map unchanged.

Install was verified afterwards, so this was not an install failure:
`tools/scratch/verify_overlay.py` reads Frosty's overlay `.sb` and finds all 38 entries with chunk
sha1s different from vanilla.

### v2 — also arm the prefab's conditions → **map went completely empty**

v2 patched `spawnedgalaxymap`: `CheckOnStart = 1` on all 38 conditions + the same flags → `alwaystrue`.
Install verified: overlay `tempest.sb` 9,122,973 B (0 B before), prefab chunk sha1
`d2e2d3db6f41` → `ded9c341d8e7`.

Result: the map rendered with **zero systems**.

**Diagnosis (important):** `bf899768-3614-11e5-aa63-b2e3b7222cc5` ("alwaystrue") is a
**ConditionSchematic asset GUID, not a plot flag**. Used as a `PlotFlagId` it is an unknown flag,
i.e. false. All 38 conditions therefore evaluated false at start and fired `OnFalse → Disable`,
which is exactly an empty map. The same mistake is latent in `build_planet_mod.py`'s documentation
(it is legitimate *only* when replacing a condition-schematic import, not a flag reference).

### The hash crack that made v2 legible

`djb` is the hash for field/type names **and** for the connection ids. Verified against
`CheckOnStart` / `PlotConditions` header hashes, then used to name the event ids:

```
PlotConditionNotificationEntityData --OnTrue (0xaa8e5552)--> SpatialPrefabReferenceObjectData --Enable  (0x8ba423e4)-->
                                   --OnFalse(0xfb1e95d9)-->                                --Disable (0xf90216b1)-->
Visible = 0x35bc69ab
```

Every condition: `TriggerOnValueChange: True`, `CheckOnStart: False`.
Script: `tools/scratch/name_event_ids.py`.

---

## 5. Open hypotheses, cheapest test first

### H1 — the conditions are edge-triggered *notifications*; availability comes from quest logic at load

Cheapest test: **v3 = `CheckOnStart = 1` only, real flags untouched.**
- If the map returns to normal → the arming itself is safe, and the 38 conditions only react to real
  flag changes. Then availability is driven by the plot logic setting those flags at runtime.
- If the map is empty again → arming the notifications is what breaks it, and this path is a dead end.

Build: `build_galaxymap_mod.py` currently always swaps flags; add a `--no-flag-swap` mode (or patch
`patch_prefab(..., flags=[])`). Keep the row patch out of v3 entirely.

### H2 — the gate is save-editable after all

Our writer can set plot flags in a save (`tools/apply_effects.py`, `tools/save_edit.py`, proven
bit-identical). The flags are *persisted* (present-but-false), so:

1. copy `Careerb191e387-0ManualSave`;
2. set `meridian_01`'s `AvailableFlag` (`714a5805-c2f8-4552-a900-35da7f980121`) to true;
3. load the copy **with no mod**.

If Saajor appears, the whole thing is a save-side lever and no mod is needed. This is 30 seconds of
work and should be tried before any further asset editing. (It also explains/refutes the earlier
"flags never true" finding: if this works, the flags are simply written by the game at story beats and
never persisted in these particular saves.)

### H3 — visibility is a property connection, not an event

`Visible` (`0x35bc69ab`) appears as a `TargetFieldId` in the 243 `PropertyConnections`. Find the
connection whose target is one of the 38 `SpatialPrefabReferenceObjectData` and whose target field is
`Visible`, and drive/inject that value directly instead of going through conditions.

Tools: parse `PropertyConnections` (`tools/scratch/prefab_wiring.py` prints the first few), resolve
`SourceFieldId`/`TargetFieldId` with `djb` against a name dictionary built from `part.names` plus
guesses (`Visible`, `State`, `Object`, `Prefab`, `Enabled`, …).

### H4 — the gate is the save-side discovery store (dead end if true)

`WorldMapSaveGameAgent` (agent idx 2) holds 26→44 runtime keys that grow at Kadara/M4/M5/Meridian
(`docs/WORLDMAP-AGENT.md`). Those keys match no asset and are runtime-allocated GUIDs; our writer
cannot insert entries. If H1–H3 fail, gating is not deliverable by asset or flag editing and the
build ships honour-system.

---

## 6. Tooling

```
python tools\probe_galaxymap_prefab.py who        # name the prefab from a dumped partition
python tools\probe_galaxymap_prefab.py map        # resolve its 46 imports to asset names
python tools\probe_galaxymap_prefab.py names      # system id -> in-game name + planets
python tools\probe_galaxymap_prefab.py verify     # prefab flags == SystemData AvailableFlags
python tools\probe_galaxymap_prefab.py unlock     # galaxymap_unlock_* -> systems
python tools\probe_galaxymap_prefab.py jumpgraph  # 80 edges, connectivity
python tools\probe_galaxymap_prefab.py gate       # 38-row swap pre-flight
python tools\probe_galaxymap_prefab.py matrix     # flags true per save (all zero)
python tools\probe_galaxymap_prefab.py avail|rows|row|part|full|locators|refs|writers

python tools\build_galaxymap_mod.py [--dry-run] [--name STEM] [--title T] [--version V]
        # 38 rows (+ prefab) -> dist\galaxy-mods\<STEM>.fbmod + <STEM>_01.archive
        # writes nothing in --dry-run; verifies from the written files afterwards

python tools\scratch\verify_overlay.py        # is the applied overlay really our chunks?
python tools\scratch\verify_overlay_v2.py     # same, plus the prefab entry and mods.json
python tools\scratch\name_event_ids.py        # djb-crack connection ids
python tools\scratch\condition_offsets.py     # locate CheckOnStart bytes in the 38 conditions
python tools\scratch\mod_offset_convention.py # archiveOffset/compressedSize conventions
python tools\scratch\mod_resource_fields.py   # sha1 vs originalSha1 semantics
```

---

## 7. Gotchas that already cost time

1. **`alwaystrue` is not a plot flag.** `bf899768-…` is a ConditionSchematic asset. Putting it in a
   `PlotFlagId` field means "unknown flag" = false. This is what emptied the map.
2. **Frosty caches by file name + version.** Overwriting the `.fbmod` with the same name/version made
   Frosty launch the **old** overlay (the 01:22 build) at 01:47 without re-applying. Fix: new file
   name and/or version, or clear the cache.
3. **Enabled ≠ applied ≠ launched.** The overlay lives in `ModData\Default\patch` and only loads via
   Frosty's launcher. Verify with `verify_overlay*.py` before trusting any in-game result.
4. **One `modify` action per listing bundle.** A real mod in the pack has 920 resources / 2,146
   actions. The 38 rows are listed under 77 bundles; `build_planet_mod.py` emits **one** action per
   asset — likely why the 3-of-50 planet-gate mod was never confirmed in game.
5. **Resource metadata must be written, not inherited:** `sha1` = sha1 of the new decompressed bytes,
   `originalSha1` = vanilla chunk sha1 from the `.sb`, `originalSize` = vanilla uncompressed size,
   `archiveOffset` = chunk header offset, `compressedSize` = 8 + zstd frame.
6. **`inst.data_offset` is relative to the data blob**, not the file: patch at
   `header_size + inst.data_offset + field.data_offset`.
7. **GUID byte order:** asset GUID fields are stored in .NET raw order; `guid_orders()` in
   `build_planet_mod.py` / `build_galaxymap_mod.py` tries be/le/rev and reports swap counts.
8. **Localization is encrypted** (key id `d66a3e06`; no `CasEncrypt.yaml` in this install), so display
   names cannot be resolved from text tables — use the sun assets (§3.3).
9. **Don't save over the test career.** All tests are load-only.

---

## 8. Where things live

```
docs/GALAXYMAP-GATE.md        full evidence chain, v1/v2 results, test recipes, 38-row appendix
docs/SYSTEM-NAMES.md          system id -> name -> planets -> unlocking beat
docs/HANDOFF.md  §7           project-level status and the original plan
tools/probe_galaxymap_prefab.py  12-subcommand probe (print-only)
tools/build_galaxymap_mod.py     the mod builder (rows + prefab, dry-run, self-verifying)
tools/scratch/*.py               one-off evidence scripts listed in §6
dist/galaxy-mods/                 built artifacts (v1 AllSystems, v2 renamed)
```

Runtime paths that matter:

```
C:\Steam\steamapps\common\Mass Effect Andromeda\                 game (read-only for us, so far)
  ModData\Default\patch\                                         Frosty's applied overlay
  Patch\Win32\galaxysystemcontent.sb                             vanilla rows
  Patch\Win32\game\levels\hubs\tempest\tempest.sb                vanilla prefab
…\Mass Effect Andromeda APWorld\Mass Effect Andromeda Mods\FrostyModManager\Mods\MassEffectAndromeda\
                                                                  Frosty's MEA mod folder (empty now)
```

---

## 9. Suggested order of work

1. Restore the owner's game (launch from Steam, or Apply with no mods) — §1.
2. **H2 first** (save-side flag write on a copy) — cheapest, no mod, and it would invalidate the
   whole asset path if it works.
3. **H1** (v3: CheckOnStart only, real flags) — one build, one launch, decisive about whether arming
   the conditions is safe.
4. Only then H3 (property/`Visible` connection) — needs the field-id name dictionary.
5. If 1–4 all fail, stop: gating ships as honour-system, and say so in the release notes.
