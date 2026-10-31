# World package — playable seed

`world/mass_effect_andromeda/` is a working Archipelago world. A real seed generates with the
vendored **Archipelago 0.6.9**, unmodified:

```
Mass Effect Andromeda : v0.1.0 | Items: 44 | Locations: 5722
Location Count: 5722   Accessibility: Full   Filling: balanced
```

Output: `tools/scratch/gen-out/AP_<seed>.zip` (multidata + spoiler). Example placements:

```
Aya: Aya Tsk Nexexch 250 Ang01done: Med Kit
Aya: Aya Tsk Nexexch Goodresultfollowup: Carnifex pistols
```

## Test suite — 26 tests, 22,664 subtests, 8.6 s

`world/mass_effect_andromeda/test/test_generation.py`, run from the Archipelago root with the
world copied into `worlds/`:

```
python -m pytest worlds/mass_effect_andromeda/test/test_generation.py -q
26 passed, 22664 subtests passed in 8.58s
```

It covers four default seeds (fill + beatable), a Kadara start, `weapon_items: false` (no weapon
items in the pool), `bool_checks_only: true` (detectors are bool-only and the pool shrinks), and
the full pool filling exactly. This is the evidence for "stable random-but-accessible order":
every seed fills and every seed can be finished.

Two bugs the suite caught:

- **Float checks were unfinishable.** The client cannot detect a float flag (no stable "done"
  semantics), so the six float locations could never be checked. They are now excluded when the
  catalogue is built.
- **`exclude_int_checks` did not match its name.** It left float checks in and only applied at
  region level. Replaced by `bool_checks_only`, which filters the location pool directly.


## What is in the package

| file | role |
| --- | --- |
| `data.py` | loads `datafiles/*.json`, assigns deterministic location/item IDs, defines the region list |
| `datafiles/checks.json` | 1,432 named checks (guid, kind, region, source asset) |
| `datafiles/items.json` | the item catalogue harvested from the game (23 weapons × 10 ranks, gear, research, powers) |
| `options.py` | `starting_region`, `weapon_items`, `exclude_int_checks` |
| `regions.py` | Tempest hub plus 11 travel regions and 20 ship/auxiliary regions; access items gate the edges |
| `items.py` | access + mission + weapon items, filler to fill the pool |
| `rules.py` | Meridian victory needs `Priority Op: Meridian` and Meridian access |
| `world.py` | World class, slot data (detectors: location id → guid/kind/region) |

## Check catalogue provenance and quality

Built by `tools/build_checks.py` from two joins (`docs/plot-flag-join.json` for every
`game/plots/` asset, `tools/scratch/join-sweep.json` for 29,834 level/journal/space assets):

- 4,169 distinct flag GUIDs are referenced by assets; **3,258 of them are save keys**
- after quality filtering: **1,432 checks** from `game/plots` (928), `game/space` (374),
  `game/journals` (80), `game/storyteller` (50)

**`game/levels/**` is deliberately excluded.** It accounts for ~1,900 more named flags, but
they are level scaffolding — `zzdebug`, `mainflow`, `objectives`, streaming triggers,
`galaxycompletiondataasset` — which makes for terrible checks. Re-admitting it needs a
semantic filter (by flag path or by which asset class references it), not a name filter.

## Packaging (`.apworld`) — verified

`tools/build_apworld.py` builds `dist/mass_effect_andromeda.apworld` (370 KB, 17 entries):

```
archipelago.json                        # container manifest
mass_effect_andromeda/__init__.py       # package, zipimport-ed as worlds.mass_effect_andromeda
mass_effect_andromeda/*.py
mass_effect_andromeda/datafiles/*.json
mass_effect_andromeda/docs/*
```

Two things had to change for the zip path to work:

1. **Data must be read through `importlib.resources`**, not `Path(__file__).parent` — inside an
   `.apworld` the package is a zip member and `open()` fails (`FileNotFoundError` on
   `datafiles/checks.json`). `data.py` now uses
   `resources.files(__package__).joinpath("datafiles/…")`.
2. **The container manifest needs the archiving protocol fields**: `compatible_version: 7`
   (APContainer protocol for 0.6.x) and `world_version` — without the latter Archipelago reports
   `v0.0.0` for the world even though the package manifest says 0.1.0.

End-to-end proof: with the folder copy removed and only the `.apworld` in
`vendor/Archipelago/custom_worlds/`:

```
MEA present: True | version: Version(major=0, minor=1, build=0) | locations: 5728
 Mass Effect Andromeda                   : v0.1.0  | Items:   44 | Locations:   5728
Creating final archive … AP_99944342256591970567.zip
```

## Running generation in this sandbox

Two environment quirks, both handled in `tools/mea_gen_run.py`:

1. The vendored venv lacks some *unrelated* worlds' packages (`zilliandomizer`,
   `pyevermizer`, `nest-asyncio`), so use the official `SKIP_REQUIREMENTS_UPDATE=1`.
2. The DSH sandbox allows writes into directories that already exist but denies writes into
   subdirectories created by the subprocess. Archipelago writes its output through
   `tempfile.TemporaryDirectory()`, so the runner redirects that to pre-created directories
   and clears them first (a stale directory once leaked a 3,259-location spoiler into a
   1,432-location seed archive — the runner now wipes them per run).

```powershell
# from the Archipelago root, with the world copied to worlds/mass_effect_andromeda
$env:SKIP_REQUIREMENTS_UPDATE="1"
$env:TMP="$root\tools\scratch\tmp"; $env:TEMP=$env:TMP
python tools\mea_gen_run.py <ap-root> tools\scratch\gen-tmp `
  --player_files_path tools\scratch\yaml --outputpath tools\scratch\gen-out --seed 7
```

The world is currently tested by copying it into `vendor/Archipelago/worlds/`; packaging it as
`.apworld` comes with the client work.

## Not done yet

- **Victory detector**: the goal is a region + mission item, but the actual in-game flag for
  completing *Meridian* is not identified yet; the client needs one real flag to report.
- **Client**: check reading and delivery exist as `tools/check_engine.py`; the AP client
  wrapper and save-watching loop are not written.
- **Items**: access/mission items have no delivery mechanism in-game yet (a Frosty mod or
  save edits must grant them).
- **Launcher**: the MEA campaign tab and mod manager are untouched.
