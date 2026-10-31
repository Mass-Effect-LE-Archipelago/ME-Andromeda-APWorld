# Handoff — Mass Effect Andromeda APWorld + randomizer

Written at round 36 of 40, for a fresh session. Everything below is verified unless marked
otherwise; the evidence files are named so nothing has to be re-derived.

---

## 1. What this project is

`C:\Users\unowi\Documents\APWorldMaker\Mass Effect Andromeda APWorld`

An Archipelago world + client + mod manager for **Mass Effect Andromeda**, plus the supporting
reverse engineering. Sibling: `C:\Users\unowi\Documents\APWorldMaker\launcher` (the Mass Effect
Archipelago Launcher, a WPF app for the Legendary Edition games, which we are extending to MEA).

Owner decisions that are settled:
- **Win condition**: complete Meridian.
- **Delivery**: save-watch first, live bridge later.
- **Mods**: use Frosty's libraries, our own UI/CLI (replace Frosty Mod Manager).
- **Build order**: full Heleus map before anything playable.

---

## 2. Status

### Done and verified

| part | evidence |
| --- | --- |
| AP world, 5,722 checks / 44 items / 20 regions | `python -m pytest worlds/mass_effect_andromeda/test/test_generation.py` → 26 tests, 22,664 subtests |
| Packaged `.apworld`, loads from `custom_worlds/` | `tools/build_apworld.py`; 376 KB; `loads: True locations: 5722` |
| Release payload (apworld + mods.json + 24 mods, checksums) | `tools/build_release.py`; `dist/release/`, `dist/release-mods/` |
| Client: save watching, checks, item queue, world-map tracking, level goal | `world/.../client.py`, `client_core.py`; tests in `world/.../test/` |
| Save parser/writer (plot flags, agents, world map) | `tools/profsave3.py`, `tools/save_edit.py`; round-trip identical |
| Batch delivery of flag edits | `tools/apply_effects.py --selftest` → PASSED |
| Mod inventory + conflicts | `data/mods.json`, `tools/fbmod.py`, `docs/MODS.md` |
| Mod manager CLI (profile, conflicts, deploy/verify/restore) | `tools/modmanager.py` |
| Launcher MEA mod subsystem (C#) | `launcher/src/.../MeaMods.cs`, `--mea-*` CLI; builds 0 errors |
| **Frosty `.fbmod` writer** | `tools/frostbite/dbwrite.py`; 13/13 byte-identical |
| **`.archive` payload writer** | `tools/frostbite/modarchive.py`; 920 chunks rebuilt |
| **First gameplay mod built** | `tools/build_planet_mod.py` → 723 B mod + 1,652 B archive, 1 asset |

### Not done (the honest gaps)

1. **General planet gating** — the objective's "stable random-but-accessible order" is logic-only;
   in game it is honour-system. This is what the next session is for (§7).
2. **Item delivery for weapons/planets** — no item→flag table; weapons are not addressable via
   research flags (`docs/SAVE-FORMAT.md`), inventory lives outside plot flags.
3. **Launcher campaign UI** — patch written, build-verified, **reverted** pending owner sign-off:
   `docs/launcher-mea-campaign.patch` (`git -C launcher apply` from the project root).
4. **Post-finale win edge case** — a player who saves only after leaving the Meridian hub is missed.

---

## 3. Where the evidence lives

Read these before re-deriving anything:

| doc | contents |
| --- | --- |
| `docs/PLAN.md` | phase log, current state |
| `docs/SAVE-FORMAT.md` | container/header/body/plot layout, writer proof, ruled-out delivery |
| `docs/EARLY-SAVE-NOTES.md` | fresh-career analysis, client evidence on real saves |
| `docs/WORLDMAP-AGENT.md` | world map agent decode, key counts, negative GUID scan |
| `docs/PROGRESSION-LADDER.md` | 14 saves in order, named flips per boundary |
| `docs/MODS.md` | mod inventory, conflicts, manager CLI |
| `docs/MODDING-LEVERS.md` | destination/system asset dumps, the 3-of-50 gate finding |
| `docs/LAUNCHER-PLAN.md` | launcher integration design + patch status |
| `docs/ASSET-NAMES.md` | four sweeps, where named flags come from |
| `docs/RE-TOOLING.md`, `docs/EXE-ANCHORS.md` | Ghidra setup, exe anchors (exe is not on the critical path) |

---

## 4. Repo map

```
data/                  checks.json (5,722), items.json, regions.json, mods.json,
                       asset-names.txt (241,004), worldmap-keys.json
world/mass_effect_andromeda/
                       world.py options.py regions.py rules.py data.py items.py
                       client.py client_core.py profsave.py
                       datafiles/ (checks/items/regions json)
                       docs/en_*.md setup_en.md  test/
tools/                 build_checks.py build_items.py build_regions.py build_apworld.py
                       build_release.py build_planet_mod.py
                       profsave3.py save_edit.py apply_effects.py check_engine.py
                       fbmod.py fbmod_write.py modmanager.py
                       frostbite/ (container reader: dbobject dbwrite partition modarchive
                                   vfs catalog compress patch cli run selftest)
                       probe_*.py progression_ladder.py name_worldmap_keys.py
                       ghidra-scripts/ ghidra/
dist/                  mass_effect_andromeda.apworld, release/, release-mods/, planet-mods/
docs/                  the evidence above
```

Saves (read-only inputs): `C:\Users\unowi\Documents\BioWare\Mass Effect Andromeda\Save`
- two finished careers (`870ee94` 78,235 flags; `ed8233e3` 70,259)
- `c8fa1bc8-*` fresh career (M0 → M1, ~300 → 1,118 flags)
- `b191e387-*` **full ordered playthrough**: M0 → M1 → Nexus → M2 → Aya → M3 → Kadara → M4 →
  M5 → Tempest → M7 → Meridian → Eos autosaves. This is the progression ladder.

Mods: `Mass Effect Andromeda Mods/` (24 `.fbmod`, 13 DbObject + 11 FROSTY v1, plus `.archive`
companions — most are PNG/JPEG icons, one is a 920-chunk EBX store).

---

## 5. How to run things

Archipelago lives at `C:\Users\unowi\Documents\APWorldMaker\vendor\Archipelago` with a venv at
`.venv\Scripts\python.exe`. Always set `SKIP_REQUIREMENTS_UPDATE=1`.

Generate a seed (temp dirs must be pre-created; see §6):

```powershell
$env:SKIP_REQUIREMENTS_UPDATE="1"; $env:TMP="$root\tools\scratch\tmp"; $env:TEMP=$env:TMP
python tools\mea_gen_run.py <ap-root> <root>\tools\scratch\gen-tmp `
  --player_files_path <root>\tools\scratch\yaml --outputpath <root>\tools\scratch\gen-out --seed 41
```

Tests:

```powershell
Copy-Item world\mass_effect_andromeda <ap-root>\worlds\ -Recurse -Force
cd <ap-root>; .venv\Scripts\python.exe -m pytest worlds/mass_effect_andromeda/test/test_generation.py -q -p no:cacheprovider
python <root>\world\mass_effect_andromeda\test\test_client_core.py
python <root>\world\mass_effect_andromeda\test\test_worldmap.py
```

Mods:

```powershell
python tools\fbmod_write.py --selftest                    # 13/13 round-trip + an edit
cd tools; python -m frostbite.modarchive                  # archive round-trip, 13 archives
python tools\build_planet_mod.py "game/space/destinations/plt/destination_plt_kadaraunc"
python tools\modmanager.py deploy "Mass Effect Andromeda Mods" profile.json <dest>
```

Launcher: `dotnet build src\MassEffectAPLauncher -c Release` in `launcher/` (0 errors baseline).

---

## 6. Environment constraints (learned the hard way)

- **Sandbox**: writes only under `C:\Users\unowi\Documents\APWorldMaker`; directories created by a
  subprocess cannot be deleted afterwards (e.g. a stray `world/.../test/tmpid88q8u2` — harmless,
  `build_apworld.py` excludes `test/`).
- **No heredocs in PowerShell**: write scripts to a file with `@'...'@ | Out-File` and run them.
  Inline `python -c` with quotes/braces fails constantly — prefer a scratch script.
- **TLS is broken for schannel clients**: `Invoke-WebRequest`/`curl` fail; `tools/fetch.py`
  (Python/OpenSSL) works. The launcher's GitHub calls fail in-sandbox for the same reason.
- npm needs a workspace cache (`tools/npm-cache`).
- Ghidra 12.1.4 + REA installed (`docs/RE-TOOLING.md`); full exe analysis stalled, byte-level
  anchors only. **The exe is not on the critical path.**
- Python is 3.14 (has `compression.zstd`); Archipelago uses its own venv (3.12).

---

## 7. THE JOB: option 3 — the galaxy-map prefab

### Established, layer by layer (do not re-walk these)

1. **Plot flags** — not the gate: the prologue→Eos boundary flips 200 runtime-allocated flags, none
   named. Galaxy agent (idx 4) holds only current system/destination.
2. **Destination assets** (`GalaxyObjectData`, 29 fields) — not the gate: Eos vs Kadara differ only
   in content fields; `IncludeInCompletion` / `ExcludeFromJournalTask` identical.
3. **System destination locators** (`SystemDestinationLocatorEntityData`) — not the gate: every
   locator in both an early-open and a late-locked system is `Visible=True` with a null-flag
   condition.
4. **Galaxy-map prefab — this is the owner.**
   `game/ui/pausemenu/galaxymap/prefabs/spawnedgalaxymap`, partition
   `e9d830c0-8980-11e5-b9be-d95347869af1`, 32 KB, 94 objects: 42 `SpatialReferenceObjectData`,
   **38 `PlotConditionNotificationEntityData`**, 1 `PrefabBlueprint` (243 property / 77 link / 116
   event connections, 92 spawned objects). It references **all six** sample jump GUIDs; nothing else
   outside `game/space` references more than one.

### What the 38 conditions are

Each has a real plot flag, `DesiredValue: True`, `TriggerOnValueChange: True`, `CheckOnStart: False`.

| save | true | present |
| --- | --- | --- |
| fresh `M0` / `M1` | 0/38 | **0** |
| 87 % | 0/38 | 38 |
| 99.5 % | 0/38 | 38 |

They are **one-shot reveal notifications** (allocate → flip true → notification → back to false), not
persistent availability. **Therefore save-side planet delivery is impossible**: a fresh save does not
contain them (`apply_batch` applied 0 of 38) and our writer only edits existing flags.

### The flag has an owner: `SystemData.AvailableFlag` (2026-10-31)

Full write-up: **`docs/GALAXYMAP-GATE.md`**. Three things the condition objects alone do not show:

1. `spawnedgalaxymap`'s 46 imports include **all 38 `game/space/systems/systemdata/systemdata_<system>`**
   rows. Each row is an 848–864-byte `SystemData` (base `GalaxyObjectData`):
   `AvailableFlag` + `VisitedFlag` + display name / category / icon.
2. **Set equality:** the prefab's 38 watched flags *are* the 38 `AvailableFlag` values — no extras,
   none missing (`probe_galaxymap_prefab.py verify`). So "reveal" and "availability" are the same
   field; the notification is the change trigger and the row is the field it reads.
3. Ten `game/plots/systems/space/galaxymap_unlock_*` plot assets **write** 34 of the 38
   (`defaultsystems`, `postayahub`, `postayavault`, `postkadara`, `postm4`, `postm5`, `postmcm`,
   `meridian`, `remnantcity`, `kettflagship`); `aya_07`, `aya_12`, `nexus_03`, `nexus_07` are gated
   inside their own system prefab. Full map: `probe_galaxymap_prefab.py unlock`.

Also verified: the `JumpToSystem` graph is complete — 80 edges over 38 systems, 0 unresolved, every
system has an inbound edge — so **availability is the only thing blocking the map** (fuel/range
aside).

So the cheapest change is one field, not a spawn entry: swap each row's `AvailableFlag` for
`alwaystrue` (`bf899768-3614-11e5-aa63-b2e3b7222cc5`), the constant, so the plot system cannot write
it back to false. Pre-flighted on all 38 (`probe_galaxymap_prefab.py gate`): the GUID occurs exactly
once per partition, the patched partition is the same length, reparses, and keeps its instance/import
counts. That is 38 tiny overrides in one `.fbmod` — smaller and more surgical than editing the 32 KB
prefab.

### Next steps

> **Test #1 failed, and that is the important result.** The 38-row build (`AvailableFlag` →
> `alwaystrue`) was installed and confirmed live — Frosty's overlay lists all 38 rows with changed
> chunk sha1s (`tools/scratch/verify_overlay.py`) — yet the map did not change. The flag is a
> **switch, not a level**: the prefab's 38 conditions are `TriggerOnValueChange: True` /
> `CheckOnStart: False` and they drive `OnTrue → Enable` / `OnFalse → Disable` on their spawned map
> objects (`djb` cracks the ids: OnTrue `0xaa8e5552`, OnFalse `0xfb1e95d9`, Enable `0x8ba423e4`,
> Disable `0xf90216b1`, Visible `0x35bc69ab`). A flag already true at load never *changes*, so no
> event ever fires.
>
> **v2 (built, deployed, tested) emptied the map — and that is the useful result.** It patched the
> prefab's 38 conditions (`CheckOnStart = 1`) plus the flags → `alwaystrue`. Install was verified
> (overlay prefab chunk sha1 changed, `tempest.sb` 9.1 MB), then the map rendered **zero systems**.
> Cause: `bf899768-3614-11e5-aa63-b2e3b7222cc5` is a **ConditionSchematic, not a plot flag** — as a
> `PlotFlagId` it reads as false, so all 38 conditions fired `OnFalse → Disable`.
>
> **Start here next: `docs/HANDOFF-GALAXYMAP.md`** — the full state, the three experiments, the `djb`
> hash crack that named the connections, and four ranked hypotheses with the cheapest test each. The
> cheapest by far is save-side: write `meridian_01`'s `AvailableFlag` true into a **copy** of the
> Tempest save and load it with no mod.
>
> If every path fails, the remaining suspect is the save-side discovery store
> (`WorldMapSaveGameAgent`, `docs/WORLDMAP-AGENT.md`), which our writer cannot extend — gating then
> stays honour-system. The steps below are kept for the record.

1. In the prefab, walk the 38 `PlotConditionNotificationEntityData` objects together with their
   `EventConnections` targets: each notification fires something that reveals a system. Identify the
   target object per condition and find the `Objects[92]` spawn entry it toggles.
2. Then choose the smallest game-side change that makes a system available at load — options to test,
   cheapest first:
   - force the spawn entry's `Visible`/`State` (locator fields we can already read/write),
   - point a notification's condition at `alwaystrue` (`bf899768-3614-11e5-aa63-b2e3b7222cc5`) so it
     fires on load,
   - patch the `PrefabBlueprint` property connection that gates the spawn.
3. Rebuild with existing tooling — `tools/build_planet_mod.py` already patches a partition, replaces
   an archive chunk, retargets the mod's resource name + bundle, and rewrites `.fbmod`; extend it to
   take this asset.
4. **Verify in game** — only the owner can. Deploy via `tools\modmanager.py`, launch MEA, check the
   map. Best save on disk for it: `Careerb191e387-0ManualSave` (`SavedGame_HUB_Tempest`, 24,031
   flags, after M5 / before M7).

### Two container rules the build had to get right (also wrong in `build_planet_mod.py`)

1. **One `modify` action per listing bundle.** A real mod in the pack has 920 resources but 2,146
   actions. The 38 system rows are listed under **77** distinct bundles; a one-action build patches
   one copy and leaves the rest. `destination_plt_kadaraunc` is listed in 8 bundles, and
   `build_planet_mod.py` emits one action — likely why the planet-gate mod was never confirmed.
2. **Resource metadata must be written, not inherited**: `sha1` = new bytes' sha1,
   `originalSha1` = vanilla chunk sha1 from the `.sb`, `originalSize` = vanilla uncompressed size,
   `archiveOffset` = chunk header offset, `compressedSize` = 8 + frame.
   `build_planet_mod.py` leaves the template's values in place.

### Known-good fallbacks if the prefab edit proves impractical

- The `alwaysfalse → alwaystrue` swap works for **3 of 50** landable destinations
  (`destination_plt_kadaraunc`, `destination_plt_kearnosii`, +1) and is already implemented and
  verified (`tools/build_planet_mod.py`, output in `dist/planet-mods/`).
- The build ships as honour-system planet order otherwise; everything else (checks, items, win) is
  real.

### Useful entry points

- `tools/frostbite/partition.py` — `Partition(data).instance_objects()` yields `(name, dict)`
  objects; imports appear as `{'__import__': '<guid>'}`; GUIDs may not decode as `Guid` objects, so
  byte-level search is often the reliable route.
- `tools/frostbite/dbwrite.py` — typed DbObject read/write (`value()` returns `(raw_tag, value)`;
  **keep the raw tag byte**, the `0x80` flag matters).
- `tools/frostbite/modarchive.py` — chunk container; layout is
  `u32be uncompressed | u16be 0x0F70 | u16be compressed | zstd frame`, repeated.

---

## 8. Gotchas that cost real time — do not re-learn these

- **Save bit reader is LSB-first within bytes.** MSB/byteswap attempts all fail.
- **`parse_plot` needs two `push_frame(24)`**; frame lengths exclude their own header.
- **`profasave3` world map**: two mirror lists — de-duplicate before counting.
- **`data["level_name"]` is always `Game/Levels/RootLevel/RootLevel`**; the save's location tag is
  header `entry1` (`SavedGame_HUB_Meridian`, …).
- **Float plot flags cannot be detected** by the client → excluded from the catalogue (5,728 → 5,722).
- **DbObject writer**: `self.pos + self.packed()` evaluates `pos` first and silently shifts frames;
  read the varint into a variable, then compute `end`.
- **Mod resources**: a mod must list exactly the assets it overrides — the first build shipped 920
  template assets by mistake before being truncated to 1.
- **`.archive` files are usually just images**; only content mods carry the chunked store.
- **AP generator**: `ModuleUpdate` aborts → `SKIP_REQUIREMENTS_UPDATE=1`; temp dirs must pre-exist.
- **Stale temp dirs** can leak old spoilers into a seed zip — the runner wipes them each run.

---

## 9. Decisions waiting on the owner

1. **Launcher patch** — apply `docs/launcher-mea-campaign.patch` and finish `Releases.cs` +
   `MainWindow.xaml.cs` detection? (Touches files shared with ME1/2/3; the patch is additive and
   builds clean, but needs the go-ahead per the workspace rule.)
2. **How far to take gating** — logic-graph edit (this handoff's job) vs shipping honour-system.
3. **Item effects** — worth chasing the entity/component section for weapon delivery, or accept
   checks-only?

## 10. First actions for the new session

```powershell
cd "C:\Users\unowi\Documents\APWorldMaker\Mass Effect Andromeda APWorld"
python tools\fbmod_write.py --selftest           # confirms the mod pipeline still works
cd tools; python -m frostbite.modarchive; cd ..
python tools\build_release.py --out dist\release  # confirms packaging still works
```

Then start §7 step 1: dump and diff the system graphs.
