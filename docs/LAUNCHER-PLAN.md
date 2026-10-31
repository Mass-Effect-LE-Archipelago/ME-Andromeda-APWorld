# Launcher: adding Mass Effect Andromeda as a fourth campaign

**Status: mod subsystem implemented and tested; the campaign UI is the remaining step.** The only
launcher changes so far are additive: `MeaMods.cs`, eight `--mea-*` CLI commands, an embedded
`options-mea.json`, and no change to any ME1/ME2/ME3 code path. The build is green (0 errors) and
the existing behaviour is untouched.

## What is done (verified)

`MeaMods.cs` owns the Andromeda mod side, which does not fit `Installer.cs`:

- reads the payload's `mods.json` inventory (built by the game project's `tools/fbmod.py`)
- keeps an ordered, per-mod-enabled profile
- reports **asset conflicts with the winner** (later in load order = wins)
- `deploy` copies enabled mods in order and writes `ap-manifest.json` with SHA-256 per file
- `verify` re-checks presence and hashes; `restore` deletes exactly the manifest's files

Driven and verified through the launcher's own CLI on the real pack:

```
--mea-modlist  → 24 mods with title, author, asset count
--mea-profile  → wrote profile with 24 mods
--mea-disable Tempest Superstore Rank 02…10 → 9 change(s) saved
--mea-status   → 15 enabled, conflicts printed with WINS
--mea-deploy   → deployed 15 mod(s) (+ap-manifest.json)
--mea-verify   → verified 15 mod(s): 0 problem(s)
--mea-restore  → removed 15 file(s), folder empty
```

## Remaining: the campaign UI — **patch prepared, awaiting go-ahead**

Per the working preference for scope sign-off before non-trivial code changes, the launcher's
shared files are **untouched right now**. The campaign change is written, build-verified and saved
as a patch instead of being applied:

```
docs/launcher-mea-campaign.patch     7.3 KB, `git apply --check` passes, builds with 0 errors
git -C launcher apply "Mass Effect Andromeda APWorld/docs/launcher-mea-campaign.patch"
```

What the patch changes (2 files, additive branches only):

- `Profiles.cs` — adds `TocMode.None` and `LoaderMode.FrostyMods`, an `MEA` GameProfile, an
  `ExePath(root)` helper (MEA's exe sits at the install root, LE games keep
  `Game\<folder>\Binaries\Win64`) and registers MEA in `GameProfile.All`.
- `Installer.cs` — `ExeDir`/`GameExe` follow the profile layout; `Install` and `LaunchProblems`
  early-return to new Frosty-mode methods that install the `.apworld`, stage an ordered mod set
  into the state folder via `MeaMods`, and report that applying mods is not automatic yet. Every
  Legendary Edition branch is textually unchanged.

What the patch does **not** touch (still needed before the campaign is complete):

- `Releases.cs` — `Complete()`/`Assemble()` assume an ASI folder and a `DLC_MOD` folder; MEA's
  payload is `mass_effect_andromeda.apworld` + `mods.json` + `mods\*.fbmod`.
- `MainWindow.xaml.cs` — the three game-folder detection sites hardcode the LE path shape and
  need to call the new `ExePath` helper.

With the patch applied, the launcher shows an Andromeda campaign that installs the world and
stages the mods, but does not yet download/verify an MEA release or apply the mods to the game.

## Proposed profile

```csharp
GameProfile MEA = new() {
    Id = "MEA", Title = "Mass Effect Andromeda",
    GameFolder = ".", Exe = "MassEffectAndromeda.exe", ProcessName = "MassEffectAndromeda",
    Apworld = "mass_effect_andromeda.apworld", Client = "Mass Effect Andromeda Client",
    OptionsResource = "options-mea.json",
    Toc = TocMode.None, Loader = LoaderMode.FrostyMods,
    ModFolder = null, DlcName = null, ModManagerGame = null,
    SaveNote = "Andromeda saves live in Documents\\BioWare\\Mass Effect Andromeda\\Save. Start a new " +
               "Ryder after the mod set is applied; the client binds the career on first connect.",
};
```

### Deployment model

1. **Detect** the install (`MassEffectAndromeda.exe` + `Data\layout.toc`), reject trial builds.
2. **Mod set** — our store at `%LOCALAPPDATA%\MassEffectAPSetup\MEA\mods\` plus `mods.json`.
3. **Profile** — ordered, enabled/disabled, with conflicts shown before apply (`MeaMods.cs`).
4. **Apply** — a helper that references the Frosty assemblies already on disk drives
   `FrostyMod`/`AssetManager`; Frosty's loader does the runtime patching, we own ordering,
   conflicts, backup and restore.
5. **Restore** — disable the mod set; vanilla data is untouched.

## Open decision

The apply step is the blocker: **A (recommended)** vendored Frosty engine + our own UI/CLI, which is
what the owner chose, requiring a small net48 helper that references the Frosty DLLs (already
proven loadable from `tools/frostyprobe`); or **B** generate a Frosty Mod Manager profile and shell
out to `FrostyModManager.exe`, which keeps Frosty in the loop.

## Data already ready for the launcher

- `launcher/src/MassEffectAPLauncher/options-mea.json` — Options page schema (starting region,
  weapon items, boolean checks; three presets), now embedded as a resource.
- `Mass Effect Andromeda APWorld/data/mods.json` — the 24-mod inventory with 1,955 assets.
- `tools/fbmod.py conflicts` / `--mea-status` — 14 asset conflicts and 8 bundle conflicts, including
  ten mutually exclusive `Tempest Superstore Rank` mods.
