# The galaxy-map gate: `spawnedgalaxymap` + `systemdata_*`

Answers the open question in `MODDING-LEVERS.md` ("find the galaxy-map asset that owns the
system list") and supersedes the earlier conclusion that availability "follows quest state, not
flags". At the **system** level it is one flag per system — the destination-level search missed it
because the field lives one layer up, in `game/space/systems/systemdata/`.

All numbers below come from `tools/probe_galaxymap_prefab.py` (commands in §7).

---

## 1. The prefab

| | |
| --- | --- |
| asset | `game/ui/pausemenu/galaxymap/prefabs/spawnedgalaxymap` |
| partition GUID | `e9d830c0-8980-11e5-b9be-d95347869af1` |
| size | 32,512 bytes (the file previously dumped as `tools/scratch/galaxymap.bin`) |
| superbundle | `Patch/Win32/...` (highest priority listing) |

How it was named: it is the only EBX asset in the install with `originalSize == 32512` whose
partition GUID equals the dumped partition's GUID (`probe_galaxymap_prefab.py who`).

Structure (`PrefabBlueprint`, 94 instances, 46 imports, 45 arrays):

```
 42  SpatialReferenceObjectData        positions / map layout
 38  PlotConditionNotificationEntityData   one per system — watches that system's AvailableFlag
  7  EntityData
  3  GameObjectData
  2  SpatialEntityData
  1  PrefabBlueprint
  1  DynamicDataContainer
 PropertyConnections 243   LinkConnections 77   EventConnections 116   Objects 92
```

Its 46 imports resolve to:

- **38 × `game/space/systems/systemdata/systemdata_<system>`** — one per system, i.e. this is the
  jumpable-system list itself;
- `game/ui/pausemenu/galaxymap/prefabs/galaxysystemlocatoruiprefab` (the per-system map widget);
- `game/ui/pausemenu/galaxymap/prefabs/galaxymapuichannel`;
- 6 imports into subtrees not indexed by the probe (icons / VFX).

`galaxymapprefab` (the UI wrapper, 20,656 bytes) imports *this* prefab, so the chain is
`galaxymapprefab` (UI) → `spawnedgalaxymap` (the map content) → 38 `systemdata_*` rows.

The human names of those 38 systems are derived from each system prefab's `spaceobject_sun_<name>`
import — see **`docs/SYSTEM-NAMES.md`** for the full table (`probe_galaxymap_prefab.py names`).

## 2. The row: `SystemData` with a single availability flag

Each row is tiny (848 bytes for aya, 864 for the rest) and holds one object:

```
game/space/systems/systemdata/systemdata_kadara_01    864 bytes, partition 2ab43031-…
  instance 0 type=SystemData   (base: GalaxyObjectData)
    Name                game/space/systems/systemdata/systemdata_kadara_01
    ObjectDisplayName   {'StringId': 27215}
    ObjectCategory      5
    AvailableFlag       {'PlotFlagId': {'Guid': d3cce618-0b27-4a64-ae60-505b6f760168}}   <-- the gate
    VisitedFlag         {'PlotFlagId': {'Guid': f197e042-e057-4ca0-8c12-94125c5201d7}}
    SectorDisplayName   {'StringId': 0}
    StarType            0
    Icon                {'__import__': …}
```

This is the `UnlockFlag`/`Available` field the earlier destination-level diff went looking for and
could not find: it exists, but on the **system** row, not on `destination_plt_*` and not on the
system `PrefabBlueprint`.

## 3. Who writes the flags: ten story-beat plot assets

`game/plots/systems/space/galaxymap_unlock_*` are `PlotLogic` prefabs whose `PlotActionEntityData`
actions set flags. Every flag they set is a `SystemData.AvailableFlag` — with one extra marker flag
per asset:

| unlock asset | systems unlocked |
| --- | --- |
| `galaxymap_unlock_defaultsystems` | nexus_01, nexus_02, nexus_04 |
| `galaxymap_unlock_postayahub` | aya_02, aya_03, aya_04, aya_11, kadara_09, nexus_09 |
| `galaxymap_unlock_postayavault` | kadara_01 |
| `galaxymap_unlock_postkadara` | aya_06, aya_09, aya_10, kadara_02, kadara_03, kadara_04, nexus_05 |
| `galaxymap_unlock_postm4` | aya_08, aya_13, kadara_05, kadara_06, kadara_11, nexus_08 |
| `galaxymap_unlock_postm5` | kadara_07, kadara_08, kadara_12, meridian_02, meridian_03, meridian_04, nexus_06 |
| `galaxymap_unlock_postmcm` | aya_01 |
| `galaxymap_unlock_meridian` | meridian_01 |
| `galaxymap_unlock_remnantcity` | kadara_10 |
| `galaxymap_unlock_kettflagship` | aya_05 |

34 of 38 systems. The other four — **aya_07, aya_12, nexus_03, nexus_07** — have their
AvailableFlag referenced inside their own system `PrefabBlueprint` (plus a neighbour:
`aya_04`, `aya_11`, `nexus_05`), so those are gated by local system logic rather than a
story-beat asset. Worth knowing before claiming "all systems covered".

## 4. The prefab watches exactly those flags

`verify`: the set of 38 flags in `spawnedgalaxymap`'s `PlotConditionNotificationEntityData`
conditions equals the set of 38 `SystemData.AvailableFlag` values, exactly — no extras, none
missing. Each watcher has `TriggerOnValueChange: True`, `CheckOnStart: False`.

So the model is: story beat → `galaxymap_unlock_*` sets the system's `AvailableFlag` → the map
prefab's watcher fires and the system becomes jumpable/visible. The open question is only whether
the map re-reads the flag when it builds (in which case a mod that points the flag at `alwaystrue`
opens everything) or whether the flag is a momentary marker and the real state is the quest logic
(more in §5).

## 5. Why the save-side search came up empty

Across **all 32 career saves** on this machine (fresh `c8fa1bc8` M0→M1, the 13-step `b191e387`
ladder, both finished careers), **0 of 38** AvailableFlags are true and **0 of 38** VisitedFlags are
true — even in the finished 74,659-flag save where every system has been flown to
(`probe_galaxymap_prefab.py matrix`).

The flags are *absent* early (a fresh M0 save has 196 bools and none of them; the 850-bool M1 save
has none either), then *present but false* from the mid-game on. So the plot system registers them
when the assets load, but nothing ever writes them true in these careers.

Two readings fit that evidence, and they do not change the mod:

- **AvailableFlag is the availability store** and it is consumed when read/visited, so stable
  snapshots always catch it false; or
- it is a *new system* marker whose true state is momentary, and the map re-derives availability from
  the plot logic at load.

Either way they are runtime/quest-driven, so they are not a save-editable delivery surface:
**a save-watch client cannot gate systems, a mod must.** And either way the right replacement is the
`alwaystrue` **constant**, not a normal true flag: a real flag can be written back to false by the
plot system, a constant cannot.

This also explains the earlier negative results: destination assets carry no availability field and
the system `PrefabBlueprint` locators have null-flag conditions, because the field lives one layer
up, on the `SystemData` row that the map widget reads
(`galaxysystemlocatoruiprefab` contains `GetGalaxyObjectUIDataEntityData`, i.e. it pulls UI data
from a galaxy object).

> Cross-reference: `MODDING-LEVERS.md` §"FOUND" reaches the same prefab from the `JumpToSystem`
> GUID side and reads the 38 conditions as one-shot reveal notifications. The two notes are the same
> facts from opposite ends; `AvailableFlag` is the field the notification watches.

## 6. The jump graph is complete

From every system `PrefabBlueprint`'s `SystemDestinationLocatorEntityData.JumpToSystem` imports,
resolved against the 38 `SystemData` instance GUIDs (`probe_galaxymap_prefab.py jumpgraph`):

- 38 systems, **80 jump edges, 0 unresolved imports**;
- **every** system has at least one inbound edge (`never a jump target: none`).

So availability is the only missing thing: once the flags are open the map is fully connected.
Flying still costs `FuelCost: 1` per edge, i.e. jump range/fuel is the only other limiter.

## 7. The mod — built 2026-10-31

One 16-byte field swap per system:

```
AvailableFlag <system flag>   ->   bf899768-3614-11e5-aa63-b2e3b7222cc5  (alwaystrue)
```

Pre-flight on all 38 assets (`probe_galaxymap_prefab.py gate`):

- the flag GUID occurs exactly **once** per partition, stored in .NET raw order
  (`.NET little-endian` fields — `be: 0, le: 1, rev: 0` for all 38);
- the patched partition is the **same byte length**, re-parses, and keeps its instance and import
  counts — 38/38, 0 problems.

Built by `tools/build_galaxymap_mod.py` (a separate tool: `build_planet_mod.py` stays untouched):

```
dist/galaxy-mods/AP_GalaxyMap_AllSystems.fbmod      38,617 bytes
dist/galaxy-mods/AP_GalaxyMap_AllSystems_01.archive 23,628 bytes
```

- 38 resources / 38 chunks / **274 actions**, every chunk reparses with
  `AvailableFlag = alwaystrue`;
- verified from the files on disk, not from memory: name, `sha1` (new bytes), `originalSha1`
  (vanilla chunk), `originalSize`, `archiveOffset`, `compressedSize`, `uncompressedSize`;
- **bundle coverage 77/77** — this is the part that matters (see below).

### Two container rules learned from a real mod here

1. **One action per listing bundle.** `betterDeconstruction.fbmod` has 920 resources but 2,146
   actions: an asset listed under N bundles gets N `modify` actions. The 38 system rows are listed
   under 77 distinct bundles total (2–13 each), so a single-action build would patch one bundle and
   leave the asset's other copies untouched.
2. **Resource field semantics** (measured, not guessed):
   `sha1` = sha1 of the **new** decompressed bytes, `originalSha1` = the **vanilla chunk** sha1 from
   the superbundle, `originalSize` = vanilla uncompressed size,
   `archiveOffset` = the chunk's 8-byte header position, `compressedSize` = 8 + zstd frame.

   ⚠️ `build_planet_mod.py` sets none of `sha1` / `originalSha1` / `originalSize` (it inherits the
   template's values) and emits **one** action for an asset that `destination_plt_kadaraunc` shows is
   listed in 8 bundles. That is very likely why the planet-gate mod was never confirmed in game, and
   it should be fixed with the same two rules before the 3-of-50 fallback is trusted.

### In-game result #1 — the flag alone does nothing (2026-10-31)

The 38-row build was applied through Frosty and the owner loaded `Careerb191e387-0ManualSave`
with it live. **No system changed.** Install was proven correct afterwards: Frosty's overlay lists
all 38 `systemdata_*` entries with chunk sha1s different from vanilla
(`tools/scratch/verify_overlay.py`), so the game did run the patched rows.

Why: the conditions are **edge-triggered**. Cracking the prefab's connection ids showed the hash is
`djb`, which named them:

```
PlotConditionNotificationEntityData --OnTrue(0xaa8e5552)--> SpatialPrefabReferenceObjectData --Enable(0x8ba423e4)-->
                                   --OnFalse(0xfb1e95d9)-->                                    --Disable(0xf90216b1)-->
```

and `Visible` = `0x35bc69ab`. Every condition has `TriggerOnValueChange: True`,
`CheckOnStart: False`. Setting the flag to `alwaystrue` means it never *changes*, so no `OnTrue`
ever fires and nothing is ever `Enable`d. The flag is a switch, not a level.

### v2 — arm the switch (built 2026-10-31)

`build_galaxymap_mod.py` now also patches `spawnedgalaxymap` itself:

- `CheckOnStart = 1` on all 38 conditions (one byte each, located through the base-type field table;
  `inst.data_offset` is relative to the data blob, so the write is at
  `header_size + inst.data_offset + field.data_offset`);
- the same 38 flags → `alwaystrue`, so the start-time evaluation is true.

```
dist/galaxy-mods/AP_GalaxyMap_AllSystems.fbmod       39,029 B   39 resources / 275 actions / 78 bundles
dist/galaxy-mods/AP_GalaxyMap_AllSystems_01.archive  34,849 B
```

Verified from the written files: every row still carries `AvailableFlag = alwaystrue`, the prefab
reparses with 38 `CheckOnStart = 1` and 38 `PlotFlagId = alwaystrue`, and all 78 bundles are covered.

#### v2 in-game result — the map went completely empty

Install confirmed first (overlay `tempest.sb` 9,122,973 B, prefab chunk sha1 `d2e2d3db6f41` →
`ded9c341d8e7`), then the owner loaded the save: **zero systems rendered.**

That is a diagnosis, not noise. `bf899768-3614-11e5-aa63-b2e3b7222cc5` is a **ConditionSchematic
asset, not a plot flag**. As a `PlotFlagId` it is an unknown flag, i.e. false, so all 38 conditions
evaluated false at start and fired `OnFalse → Disable` — an empty map.

**Lesson: `alwaystrue` may only replace a condition-schematic import** (as `build_planet_mod.py`
does), never a flag reference. Any future attempt must keep the original flag GUIDs and make them
true some other way (save write, or a different condition value).

Recovery: the mod files were removed from Frosty's folder; the overlay is cleared by applying with no
mod, or by launching from Steam. Nothing was written into the game's own `Data`/`Patch` files.

### Still unproven

1. **In game.** Deploy the mod, load a save where the Tempest exists, and see whether systems that
   are normally locked are selectable. This is the only step that proves the field is what the map
   reads.
2. **The four self-gated systems** may additionally need their local prefab condition relaxed.
3. **Whether `VisitedFlag` also hides a system** ("undiscovered" vs "not jumpable"). It is false
   everywhere too, so if it were a hide-condition nothing would show; still, the first in-game test
   should check both.

### Test recipe (owner) — v2

1. v2 deployed 2026-10-31 to
   `…\Mass Effect Andromeda Mods\FrostyModManager\Mods\MassEffectAndromeda\` as
   `AP_GalaxyMap_AllSystems.fbmod` + `_01.archive` (SHA-256 verified against `dist/galaxy-mods/`).
   The files changed since test #1, so **refresh and re-apply** in Frosty before launching.
2. Launch from Frosty, load `Careerb191e387-0ManualSave` (`SavedGame_HUB_Tempest`, after M5,
   before M7). Do not save while testing.
3. Open the galaxy map. v2 arms all 38 switches, so the expected result is **not** two systems but a
   large change: every system in the cluster should be present and selectable, including
   **Tafeno** and **Saajor** (§ `SYSTEM-NAMES.md`).
4. If v2 also changes nothing, the condition→Enable path is not the reveal either; the remaining
   suspect is the save-side discovery store (`WorldMapSaveGameAgent`), which our writer cannot
   extend — at that point gating is honour-system for the build.

## 8. Reproduce

```
python tools\probe_galaxymap_prefab.py who        # name the prefab from the dumped partition
python tools\probe_galaxymap_prefab.py part  game/ui/pausemenu/galaxymap/prefabs/spawnedgalaxymap
python tools\probe_galaxymap_prefab.py map        # resolve its 46 imports to asset names
python tools\probe_galaxymap_prefab.py rows       # the 38 system rows
python tools\probe_galaxymap_prefab.py avail      # every AvailableFlag with ladder position
python tools\probe_galaxymap_prefab.py unlock     # unlock assets -> systems
python tools\probe_galaxymap_prefab.py names      # system id -> in-game name + planets
python tools\probe_galaxymap_prefab.py matrix     # flags true per save (all zero)
python tools\probe_galaxymap_prefab.py verify     # the three sets agree
python tools\probe_galaxymap_prefab.py jumpgraph  # 80 edges, fully connected
python tools\probe_galaxymap_prefab.py gate       # pre-flight the 38 swaps
python tools\scratch\verify_overlay.py            # did Frosty really install our chunks?
python tools\scratch\name_event_ids.py            # djb-crack the prefab's connection ids
```

## Appendix: the 38 system rows

| system | AvailableFlag | unlocked by |
| --- | --- | --- |
| aya_01 | `e49041e3-0643-406a-9c3f-b731506c01bf` | postmcm |
| aya_02 | `9ad92b61-ace3-410b-80f7-546569920132` | postayahub |
| aya_03 | `3608ad27-d2ce-4f7c-88ee-2120c1fe01c9` | postayahub |
| aya_04 | `77c5c0dd-7003-4c7d-aa2b-697cafbe016b` | postayahub |
| aya_05 | `06d62e23-bc2f-40bb-98c0-72af25c40146` | kettflagship |
| aya_06 | `7625031e-726d-4a44-916b-78fcd6c1019f` | postkadara |
| aya_07 | `b568e907-25f4-482d-afdc-1b4285770144` | own system prefab |
| aya_08 | `7bb13f97-6189-42af-a82d-3eec8ef20182` | postm4 |
| aya_09 | `3b4bed8b-5259-4e5d-8bbe-52f3dc0d011f` | postkadara |
| aya_10 | `25651324-573e-4129-944c-624cd14d016e` | postkadara |
| aya_11 | `1cdca27f-7a92-4781-98e9-2c8013e40134` | postayahub |
| aya_12 | `78bfa548-53c7-40e9-96c4-c420dabd0145` | own system prefab |
| aya_13 | `63b560ec-d299-4f5f-a840-cda5d93001f1` | postm4 |
| kadara_01 | `d3cce618-0b27-4a64-ae60-505b6f760168` | postayavault |
| kadara_02 | `874d381f-7da3-4d8b-95b5-939afcd601c6` | postkadara |
| kadara_03 | `0153108f-bee9-4c23-ab82-c450d0170123` | postkadara |
| kadara_04 | `a0776a60-5fb0-49ab-92d1-140bea970184` | postkadara |
| kadara_05 | `4df59824-5565-4414-835c-1d0e3a5d01d8` | postm4 |
| kadara_06 | `41d4de3f-10d2-405a-8338-5d2773b401a8` | postm4 |
| kadara_07 | `46bde4da-97df-4a89-b22c-7059e49301c1` | postm5 |
| kadara_08 | `a031422e-3b68-4a12-8edd-685772eb0179` | postm5 |
| kadara_09 | `50b69a21-2a71-407a-bfde-f386a66c01ee` | postayahub |
| kadara_10 | `73055793-8085-44b8-9088-9ae247f90154` | remnantcity |
| kadara_11 | `cb1fbb51-100a-4b3e-bc73-a0c34cd80182` | postm4 |
| kadara_12 | `daaed09a-e6ab-467e-8e27-03e16a690197` | postm5 |
| meridian_01 | `714a5805-c2f8-4552-a900-35da7f980121` | meridian |
| meridian_02 | `efaf9129-7d12-49d4-92d1-6418d07c01fc` | postm5 |
| meridian_03 | `879e8675-a391-46f6-b5ef-cb1d00ef012f` | postm5 |
| meridian_04 | `3b496bf5-0548-442d-b355-9473341b017d` | postm5 |
| nexus_01 | `7a584ac3-29f7-47c4-b725-b39bf6c5010a` | defaultsystems |
| nexus_02 | `dc78c421-0f8a-4d98-b330-1d6ac9390179` | defaultsystems |
| nexus_03 | `a301f01a-6881-4c96-aed7-be7aedab011e` | own system prefab |
| nexus_04 | `7e1f9d8b-f369-4526-b97c-7882dbba01b3` | defaultsystems |
| nexus_05 | `39a874ed-729d-409f-850e-a5f25df90197` | postkadara |
| nexus_06 | `d07143c6-ea96-416e-be02-d6a0962b01a0` | postm5 |
| nexus_07 | `5d424429-81df-44d2-9c08-d25492a90190` | own system prefab |
| nexus_08 | `335a69c7-71f2-4660-9ca6-d08cb4400121` | postm4 |
| nexus_09 | `bc9b9479-1382-4ad8-897a-734204bb0108` | postayahub |
