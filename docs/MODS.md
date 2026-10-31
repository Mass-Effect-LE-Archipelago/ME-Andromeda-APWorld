# Mods: inventory, formats, conflicts

The launcher's mod manager starts with knowing exactly what each `.fbmod` replaces.
`tools/fbmod.py` parses both container generations and reports the inventory and collisions.

## Formats (verified against the owner's pack)

**FBMODV2** — a Frostbite DbObject, parsed with the same reader the container tool uses:

```
magic=FBMODV2, gameProfile, gameVersion, title, author, category, version, description,
icon, screenshots[], resources[], actions[]
resources[]: { name (EBX path), type (ebx|embedded), archiveIndex, archiveOffset,
               compressedSize, uncompressedSize, shouldInline }
actions[]  : { resourceId, type (modify|add), bundle }
```

**FROSTY** (v1) — older binary header: `FROSTY\0\1`, profile string, then title / author /
category / version / description, then the payload. Metadata is read from the header strings;
asset paths and target bundles are recovered as plaintext. **Caveat:** a v1 mod's payload can
be compressed, so its asset list is a lower bound, not a complete inventory.

## The owner's pack

24 mods, **1,955 distinct assets**, 11 of them FROSTY v1 and 13 FBMODV2:

| mod | author | category | assets | bundles |
| --- | --- | --- | --- | --- |
| MEA_Fixpack_1.05d | NightWolf2503 | Bug Fixes | 187 | – |
| betterDeconstruction | itsYiyas | Gameplay | 920 | 10 |
| Increased Outlaws Spawns | Kahmu | Gameplay | 645 | – |
| Increased Research Data Point Income | Taamro | Gameplay | 93 | – |
| FixesAddendum | KrrKs | Bug Fixes | 37 | – |
| Nomad ND2 One-Click Mining Doubled Minerals | Eddga | Gameplay | 34 | – |
| Researchable Halberd | KrrKs | Crafting, Weapons | 22 | 7 |
| Enhanced Statistics Page | Kahmu | UI | 11 | – |
| Better Quantity Selection Screen | KrrKs & Kahmu | UI | 2 | – |
| Dynamic Compass | Drakenreiter | HUD | 2 | – |
| Cheap Respec | watafuzz | Gameplay | 1 | 1 |
| Tempest Superstore Rank 01…10 | Kjaro | Crafting | 1 each | 1 each |
| Faster Quest Tracker Hiding - 5 Seconds | Kahmu | HUD | 1 | – |
| FA - Drack and Kesh Conversation Changes | KrrKs | Bug fixes | 1 | – |

## Conflicts found

**14 asset conflicts, 8 bundle conflicts.** The important ones:

1. **`Tempest Superstore Rank 01…10` are mutually exclusive.** All ten replace
   `game/loot/drops/merchants/loot_merchant_tempest` and target the same bundle
   (`win32/game/levels/hubs/tempest/2401_dsg_researchroom`). Load order decides the winner;
   only one can be in a profile.
2. **MEA_Fixpack vs betterDeconstruction** — 11 shared research-project assets
   (`researchproject_gear_arms_*`, `researchproject_weapon_*`).
3. **FixesAddendum vs Increased Research Data Point Income** — 2 shared POI interaction assets
   (`poi_interaction_driftingshuttle`, `poi_interaction_liamloyaltydebris`).
4. **ResearchableHalberd vs betterDeconstruction** — shared `win32/game/mastersharedbundle`
   plus five `*_bundle` loot containers.

## Commands

```powershell
python tools\fbmod.py list "Mass Effect Andromeda Mods" --json data\mods.json
python tools\fbmod.py show "Mass Effect Andromeda Mods\Cheap Respec.fbmod"
python tools\fbmod.py conflicts "Mass Effect Andromeda Mods"
```

`data/mods.json` holds the full inventory for the launcher to consume.

## Mod manager CLI — working

`tools/modmanager.py` is the piece the launcher will call. It owns an ordered, conflict-aware
profile and a verifiable deploy/restore:

```powershell
python tools\modmanager.py init      "Mass Effect Andromeda Mods" profile.json
python tools\modmanager.py status    "Mass Effect Andromeda Mods" profile.json
python tools\modmanager.py disable   profile.json "Tempest Superstore Rank 02.fbmod" ...
python tools\modmanager.py conflicts "Mass Effect Andromeda Mods" profile.json
python tools\modmanager.py order     profile.json "Cheap Respec.fbmod" 5
python tools\modmanager.py deploy    "Mass Effect Andromeda Mods" profile.json <dest>
python tools\modmanager.py verify    <dest>
python tools\modmanager.py restore   <dest>
```

`deploy` copies the *enabled* mods in order and writes `ap-manifest.json` with each file's
SHA-256; `verify` re-checks presence and hashes; `restore` deletes exactly the manifest's files,
so a failed experiment can never leave a half-changed folder.

Verified on the real pack:

```
deployed 16 mod(s) to …\deployed (+ap-manifest.json)     # 17.6 MB
verified 16 mod(s): 0 problem(s)
  CHANGED Cheap Respec.fbmod                             # after corrupting one on purpose
verified 16 mod(s): 1 problem(s)
restored …: removed 16 file(s)                           # folder back to empty
```

Disabling `Tempest Superstore Rank 02…10` before checking conflicts removes that ten-way clash
from the report, which is the intended workflow: the profile is the conflict resolution.

## Integration plan

- **v0 (inventory + profiles)**: our launcher reads `mods.json`, lets the owner toggle mods and
  order them, and shows the conflicts above before anything is applied.
- **v1 (apply)**: use Frosty's libraries (already on disk: `FrostyCore`, `FrostySdk`,
  `FrostyHash`, `Mea.json` profile) as the engine that builds the patched bundles, while our
  launcher owns the UI, order, conflict rules, backup and restore. That is the option the owner
  chose ("use Frosty's libraries, our own UI/CLI").
- **v2 (AP mod generation)**: emit our own `.fbmod` for a seed (plot hooks, shop seeding,
  starting state) from the same generator, so a seed ships an `.apworld` + a mod + a client.

## Not done yet

- No mod is applied to a game yet: this round only proves the inventory and conflict model.
- Applying needs a Frosty-engine harness (C#) and a restore path, neither written.
