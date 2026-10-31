# RE tooling

Installed 2026-10-30, entirely inside this project folder so the sandbox permits it.

| Component | Version | Location |
| --- | --- | --- |
| Ghidra | 12.1.4 (2026-09-21) | `tools\ghidra\ghidra_12.1.4_PUBLIC` |
| JDK (Ghidra needs a full JDK) | 21.0.12.1 | `C:\Program Files\Java\jdk-21.0.12.1` (pre-existing) |
| REA CLI | 6.5.0 | fetched by `npx`, cached in `tools\npm-cache` |
| Ghidra scripts | — | `tools\ghidra-scripts` |
| Ghidra projects | — | `tools\ghidra-projects` |
| Ghidra settings | — | `tools\ghidra-user` (redirected `APPDATA`/`LOCALAPPDATA`) |

Ghidra zip verified against the release's published SHA-256
(`ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db`).

## Use it

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force      # the .ps1 is not code-signed
. .\tools\rea-env.ps1

rea doctor --json                                     # expects ghidra: ok
ghidra-headless <projdir> <projname> -import <binary> -noanalysis -postScript ScanSaveStrings.java
ghidra-headless <projdir> <projname> -process <program> -postScript DumpSaveRefs.java
```

`rea` exposes 153 CLI commands (`analyze`, `decompile`, `annotate-native-function`, …) that
drive Ghidra headlessly. The REA MCP server is *not* registered in this DSH session (its
registration would rewrite `C:\Users\unowi\.dsh\cordis.patch.yml`, outside the workspace),
so the CLI is the interface. Everything below works through the CLI.

## Environment traps found while installing

1. **Ghidra 12.2 needs Java 25.** The machine has Java 21, so 12.2 refuses to start
   (`application.java.min=25`). Ghidra **12.1.4** is the newest release that runs on the
   installed JDK 21. REA's own check also asks for "Ghidra 12.1.x".
2. **Java 21 on this machine is a JDK, but not where Ghidra looks.** `JAVA_HOME` was unset,
   so the launcher prompted for a JDK and then failed. `rea-env.ps1` sets it.
3. **Ghidra writes settings to `%APPDATA%\ghidra`, which the sandbox denies** (`Access is
   denied` on `java_home.save`). `rea-env.ps1` redirects `APPDATA`/`LOCALAPPDATA` into
   `tools\ghidra-user`.
4. **Windows schannel TLS fails here** (`SEC_E_NO_CREDENTIALS`), so `Invoke-WebRequest` and
   `curl.exe` cannot download anything. Clients with their own TLS stack work: `npm`/`npx`
   and Python. Use `tools\fetch.py` for downloads.
5. **npm's cache defaults outside the workspace** and is blocked; `npm_config_cache` points
   it at `tools\npm-cache`.

## First result: the executable's save/plot anchors

`ScanSaveStrings.java` scanned the initialised memory of
`MassEffectAndromeda.exe` (75.6 MB, no analysis needed) and found **276** matching strings,
including the whole plot-flag class family:

```
0x142c9ae88  FBCHUNKS
0x142c92568  FBHEADER
0x142fdd4f8  BioMetrics_PlotStartMarker
0x142fdd800  PlotSaveGameAgent
0x142fde630  PlotFlagReferenceA        0x142fde6a8  PlotFlagReferenceB
0x142fdeaf8  PlotFlagDebugType         0x142fdeb10  PlotFlagDebugSymbol
0x142fdeba0  PlotPlotFlagValueUpdateMessageBase
0x142fdd980  PlotFlagIdSemantics_Boolean / _Integer / _Float / _Transform / _Invalid
0x142fddb60  PlotFlagsDefaultValues    0x142fddb78  NewGamePlusPlotFlags
0x142fdec28  PlotIncrementIntegerByPlotFlagValueEntityData
0x142d7a7e8  WorldStateManager
0x142d7e538  MEJournalSystem (+ CategoryContainer, Category, CategoryType)
```

Also present: `GalaxyDataManager` (8), `PartyManager` (32), `CodexList` (33), `ActivePlayTimer`
(31), `WorldMap` (25), `Notifications` (17), `LootContainer` (8), `SaveGame` (10),
`JournalSystem` (34). `PlotFlagIds`, `PlotFlagsDefaultValues` and `NewGamePlusPlotFlags` are
strong candidates for the tables that map plot flags to their identifiers — the missing link
between the save's GUIDs and human names.

## Artifacts

- `tools\ghidra-projects\MEAString` — imported program (analysis started 2026-10-30).
- `tools\ghidra-projects\mea-strings.log` — raw string scan (276 hits).
- `docs\ghidra-save-refs.txt` — anchor xrefs and plot/save function list, written by
  `DumpSaveRefs.java` after analysis completes.
