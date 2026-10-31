# Mass Effect Andromeda — Archipelago world, client, mod manager

Status: **world generates, save I/O works, mod inventory works; in-game effects blocked on data** (2026-10-30)
Owner: unowi. Sibling projects: `../ME3 LE Randomizer`, `../ME2 LE Randomizer`, `../MassEffectRandomizer`, `../launcher`.

## Progress so far

- **P1 (extraction)**: Frostbite content layout identified; Frosty Tool Suite 1.0.6.3
  assemblies load and reflect (`tools/frostyprobe/`). **Asset name index built**:
  241,004 unique names extracted from `.sb` metadata (`data/asset-names.txt`), including
  1,147 plot assets and the full journal mission tree. Cas/partition reader in progress
  (`tools/frostbite/`). No GUID ↔ name join yet.
- **P2 (save format)**: **reader and writer done** — container, 19-entry header, full
  bit-stream body, 13 agent tables, plot block. Reader: 74,659 bools / 3,326 ints /
  250 floats. Writer: plot block re-encodes bit-identically; edits keep CRC/size valid.
  `tools/check_engine.py` turns saves into check events and applies deliveries
  (self-test passes). In-game acceptance not yet tested.
- **P3 (world)**: **playable seed generates** in Archipelago 0.6.9 — **5,722 checks**, 44 items,
  11 travel regions + 20 auxiliary regions, Meridian goal. **Packaged** as
  `dist/mass_effect_andromeda.apworld` and verified loading from `custom_worlds/` and generating
  from the zip (`v0.1.0`, 5,722 locations). **Test suite green**: 26 tests / 22,664 subtests in
  8.6 s (`world/.../test/test_generation.py`, covers four seeds, starting region, weapon items
  off, bool-only checks, exact pool fill). See `docs/WORLD-BUILD.md`.
- **P4 (client)**: `world/.../client.py` + `client_core.py` — save watcher, check detection and
  an item queue. Offline tests pass on real saves; the module imports in Archipelago 0.6.9.
  Item *effects* wait on flag data. See `docs/CLIENT.md`.
- **Item/goal effects**: **a full playthrough arrived** (career `b191e387`, M0 → Meridian → Eos,
  14 saves in order) and produced `docs/PROGRESSION-LADDER.md`. **The world map agent is decoded**
  (`docs/WORLDMAP-AGENT.md`): `WorldMapSaveGameAgent` (idx 2) holds 1 → 3 → 4 → 33 map entries as
  the story advances, so it *is* the galaxy discovery store; the galaxy agent (idx 4) only tracks
  the current system. Planet unlock detection and delivery both hinge on naming those entries,
  which needs each `game/space/**` asset's own EBX GUID indexed (not its partition GUID).
- **Delivery mechanism**: **built and verified** — `tools/apply_effects.py` writes N flags in one
  rewrite with a backup and a verification pass. The item → flag table is missing; two candidate
  sources are ruled out (weapon research flags are shared; no named win flag exists), so the next
  step is decoding the component-container section of the save.
- **P5 (mods / launcher)**: **mod inventory, conflict model and mod-manager CLI done** —
  `tools/fbmod.py` parses both `.fbmod` generations; 24 mods, 1,955 assets, 14 asset + 8 bundle
  conflicts (`docs/MODS.md`, `data/mods.json`). `tools/modmanager.py` adds profiles, ordering,
  conflict reporting, deploy with SHA-256 manifest, verify and restore — all verified on the real
  pack. Launcher C# integration is planned in `docs/LAUNCHER-PLAN.md` (the launcher builds clean,
  0 errors); the apply step needs sign-off.
- **World model**: regions and the codename → planet mapping established with evidence
  (`data/regions.json`, `docs/WORLD-MODEL.md`); priority-op mission ladder identified from
  `game/journals/`.
- **RE tooling**: Ghidra 12.1.4 + REA 6.5.0 CLI installed (`docs/RE-TOOLING.md`); byte-level
  anchors in `docs/EXE-ANCHORS.md`. The exe is not on the check-catalogue critical path.
- Tooling: `tools/frostbite/` (container reader), `tools/build_checks.py`,
  `tools/build_items.py`, `tools/build_regions.py`, `tools/check_engine.py`,
  `tools/mea_gen_run.py`, `tools/profsave3.py`, `tools/save_edit.py`, `tools/sb_names.py`.


## 1. What we are building

1. An AP world (`mass_effect_andromeda`) that turns Andromeda's campaign into a multiworld randomizer:
   start on the Tempest with one or two destinations open, everything else — planets, regions, story beats,
   squadmates, weapons, Nomad upgrades, cryo pods — arrives as items from the multiworld, and the seed concludes
   at a defined win state.
2. A client that watches the actual game and turns what happens in it into checks, and delivers items back.
3. Launcher integration: a Mass Effect Andromeda campaign beside ME1/2/3, deploying the AP mod **and the owner's
   Frosty mod set** with conflict/load-order control — our own mod manager, so Frosty Mod Manager is not needed.

The owner's stated priorities, in order: **maximum check coverage ("check slop")**, **stable random-but-accessible
order**, **mod integration**, **a real finish line**.

## 2. Ground truth collected so far

Full evidence log: `RECON-2026-10-30.md`. The load-bearing facts:

| Fact | Value |
| --- | --- |
| Backup copy | `..\Mass Effect Andromeda` — 48.81 GB, 797 files, complete Steam layout |
| Live install | `C:\Steam\steamapps\common\Mass Effect Andromeda` (same build, **unmodded**: no ASI/DLL injected) |
| Engine | Frostbite 3 — `Data\layout.toc`, `Data\Win32\*.sb/.toc/.cas`, `Patch\`, `Update\` |
| Data volume | 52 `.cas` (43.6 GB), 106 `.sb` (457 MB), 107 `.toc` (8.7 MB), 14 `.cat` |
| Bundles present | `game, launch, loc, locfacefx, loctext, opt, postlaunch, sbd, streaminginstall` |
| Mod format | `.fbmod` = `FROSTY` container, profile `MassEffectAndromeda`, list of EBX asset overrides |
| Mod toolchain on disk | Frosty Tool Suite **1.0.6.3**, .NET assemblies (`FrostyCore`, `FrostySdk`, `FrostyHash`, `FrostyModSupport`) + `MassEffectSDK.dll` profile |
| MEA saves on this machine | **none** — `%USERPROFILE%\Documents\BioWare\Mass Effect Andromeda` does not exist (game never run) |

Two consequences that drive the whole design:

- **All game content is reachable statically.** Plot flags, quests, planets, items and shops live in EBX assets
  inside those bundles, so the check catalogue can be generated from the game itself rather than from a wiki.
- **The save format is the critical unknown.** No MEA save exists here yet, and MEA is the only Mass Effect that
  does not use the `.pcsav` format our existing code parses.

## 3. Architecture

### 3.1 World package

Same shape as the LE worlds, so the launcher, tooling and tests carry over:

```
world/mass_effect_andromeda/
  archipelago.json      game name, versions
  data.py               generated tables: locations, items, regions, requires
  locations.json        generated location catalogue (stable ids)
  options.py            option groups + presets
  world.py              regions/rules/items/completion
  client.py             Archipelago client
  client_core.py        delivery contract (item -> game operation)
  delivery_client.py    transport (pipe or save-file channel)
  history*.py           cross-session delivery memory
  docs/en_Mass Effect Andromeda.md, docs/setup_en.md
  test/
```

Item and location IDs are derived from a committed manifest hash, exactly as LE3 does, so a world update cannot
silently remap an existing seed.

### 3.2 Regions and progression model

Regions are the game's own travel graph, not a new invention:

- `Tempest` — hub, always open (start state).
- `Hyperion` / `Nexus` — prologue and hub story beats.
- Open worlds: `Eos`, `Voeld`, `Havarl`, `Kadara`, `Elaaden`.
- Space-only: `Aya`, `H-047c`, `Meridian`, plus the `Ark`/`Nexus` interiors.
- Finale: `Meridian: The Way Home`.

Core progression items:

- **Planet Access** (Eos/Voeld/Havarl/Kadara/Elaaden/Meridian) — the travel gates.
- **Region/Mission Access** — priority ops, ally recruitment, loyalty missions, outpost access.
- **Weapons / Armour / Nomad upgrades / Cryo pods** — the gear layer the owner asked for.
- **Squadmates** — recruited as items.
- Filler: research points, credits, resources (the natural "salvage" of this game).

A `starting_planets` option controls the owner's requirement #1 (one or two destinations open at the start).
Native story order is preserved as *reachability*, not as a hard chain: each region edge requires its access item
plus whatever the vanilla game itself requires, so the randomizer can reorder travel without producing
unplayable states. Aim: **no excluded locations** — MEA autosaves aggressively and nearly everything is
replayable, unlike LE3's one-shot mission pickups.

### 3.3 Checks

Generated from EBX + observed save deltas, grouped per planet. Candidate families:

1. Quest/mission objectives and completions (the bulk; thousands of plot flags exist).
2. Planet progress: monoliths, vaults, forward stations, outposts, viability thresholds.
3. Remnant sites, kett bases, enemy camps, architect kills.
4. Scannables: datapads, terminals, corpses, flora/fauna, minerals, "Pebee" scans.
5. Gear: research unlocks, crafting schematics, shop stock, Nomad upgrades, cryo pods, strike teams.
6. Conversation/dialogue/romance flags (cheap checks, high slop value, low stakes).
7. Nexus/Ark side content, AVP milestones, colony/outpost choices.

Categories get per-category options (as LE3 does: `objective_checks`, `codex_checks`, …) so a seed can be
tuned from "story only" to "every scannable in Heleus".

### 3.4 Delivery: two modes, in this order

- **v0 — save-watch (ship this first).** The client polls the save folder, parses `PROFSAVE`, diffs plot flags
  against the last seen state, reports checks, and applies pending item deliveries by writing them into the save
  when the game is not running. No injection, no crash risk, works with any Frosty setup, and is the same
  history/delivery pattern the LE3 world already proves out.
- **v1 — live bridge.** A DLL injected by our launcher (we own process launch; Frosty also injects, so there is a
  known injection point to reuse) talking over the named pipe with LE3's `DEV_*` command protocol. This gives
  live check reporting and instant delivery. Requires locating MEA's plot/save manager in native code — this is
  where Ghidra/REA work on `MassEffectAndromeda.exe` (75.6 MB) and the gameplay modules goes.

v0 is the safety net: if v1 proves fragile, the world is still fully playable.

### 3.5 Mod management

- `.fbmod` is a documented, simple container; EBX overrides are path-indexed. We can **generate** an AP mod
  (plot-flag hooks, shop seeding, starting-state edits) and **apply** the owner's 20+ existing mods ourselves.
- Preferred implementation: reference `FrostyCore.dll`/`FrostySdk.dll` (already on disk, same .NET era as the
  launcher) as libraries instead of reimplementing Frostbite containers. Licence must be checked before vendoring;
  the launcher is already GPL-3.0.
- Deliverables: load-order list, per-mod enable/disable, conflict report (same EBX path touched twice), profile
  save/load, and a "vanilla restore" that provably removes every patched file — the launcher already does this
  for LE, so it is the same pattern.
- Mods in scope from the owner's folder: `MEA_Fixpack_1.05d`, `FixesAddendum`, `Weapon Overhaul`,
  `Unavailable_Guns`, `Increased Outlaw Spawns`, `Increased Research Data Point Income`, `NomadND2`,
  `ResearchableHalberd`, `Tempest Superstore Rank 01–10`, `Cheap Respec`, `betterDeconstruction`,
  `Dynamic.Compass`, `Enhanced_Statistics_Page`, `Faster_Quest_Tracker_Hiding_5s`, `BetterQuantitySelectionScreen`,
  `FA_DrackAndKeshConversationChanges` (note: several are *already* randomizer-relevant, e.g. research income and
  shop ranks are economy knobs we may want to fold into options instead of shipping as mods).

## 4. Phases and exit criteria

| Phase | Work | Exit criterion |
| --- | --- | --- |
| P0 | Recon + design (this document) | Owner approves direction and the four open questions |
| P1 | Frostbite extraction: `layout.toc` → `sb`/`toc` → `cas` → EBX dump; index every EBX path | A searchable EBX index of the game (paths + asset bodies) and a plot-flag/quest table |
| P2 | `PROFSAVE` parse + write; flag diff engine | Round-trip a real save unchanged; a one-flag edit loads in game |
| P3 | World package: data, options, regions, rules, completion | `python -m pytest` green; a generated seed's logic graph walkable; spoiler log sane |
| P4 | Client v0 (save-watch, checks, delivery, history) | A real play session reports checks and delivers on reload |
| P5 | AP mod generation + mod manager + launcher MEA tab | Launcher installs/uninstalls AP + user mods into a clean game and restores it |
| P6 | v1 live bridge, polish, docs, release payload | Full seed completed start → Meridian without manual save editing |

Ordering note: P1 and P2 are independent research tracks and can run in parallel; P3 only needs P1's tables,
P4 only needs P2.

## 5. Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| `PROFSAVE` format unknown and no save on disk | **High** | Get one save early; borrow public RE work; validate every write against a byte-identical round-trip |
| Frostbite runtime hooking is far less documented than UE3 | High | v0 save-watch ships the world without it; v1 is additive |
| Quest gating may live in native code, not EBX | Medium | Frosty mods already patch plot flags and triggers (see `FixesAddendum` notes), so the mechanism exists; validate per gate |
| Plot-flag names are opaque ids | Medium | Cross-reference EBX tables + localized strings in `loctext` bundles to get human names for the location list |
| Check count explodes past AP UI comfort | Medium | Categories and per-category caps, exactly like LE3's war-asset threshold |
| Frosty licence / vendoring | Low | Verify licence text before linking; GPL-3.0 launcher is compatible with GPL |

## 6. Open questions for the owner

1. **First save.** MEA has never been run here. Do you want to play to a first save (fastest truth), or should
   I start from public format research and validate later?
2. **Win state.** Default proposal: complete *Meridian: The Way Home*, gated behind Meridian Access plus a
   number of completed planets. Alternative: "100% viability on N planets". Which?
3. **Delivery mode.** v0 save-watch first (recommended) or straight to the injected live bridge?
4. **First vertical slice.** Eos + Nexus + Tempest + Meridian gate end-to-end, then scale to all planets
   (recommended), or attempt the full map before any playable build?
