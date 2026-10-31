# Executable anchors (MassEffectAndromeda.exe)

A raw string scan of the shipped executable (75.6 MB) and a narrow xref scan. No full
disassembly was completed: Ghidra's analysis ran ~30 minutes on one core and was stopped
before finishing, so everything here is from byte-level scanning.

## Plot/save strings found (virtual addresses, image base 0x140000000)

```
0x142C92568  FBHEADER
0x142C9AE88  FBCHUNKS
0x142FDCF30  PlotFlagIds
0x142FDD4F8  BioMetrics_PlotStartMarker
0x142FDD7C8  LastPlotFlagSet
0x142FDD800  PlotSaveGameAgent
0x142FDD818  IPlotFlag
0x142FDD888  IPlotFlag
0x142FDDB60  PlotFlagsDefaultValues
0x142FDDB78  NewGamePlusPlotFlags
0x142FDDBB0  PlotFlagsDefaultValues
0x142FDDC38  PlotFlagDebugSymbol
0x142FDEB10  PlotFlagDebugSymbol
```

Plus, from the same scan: `PlotFlagReferenceA/B`, `PlotFlagValue`, `PlotFlagId`,
`PlotFlagIdSemantics_{Boolean,Integer,Float,Transform,Invalid}`,
`PlotIncrementIntegerByPlotFlagValueEntity(Data)`, `PlotPlotFlagValueUpdateMessageBase`,
`WorldStateManager`, `MEJournalSystem(+Category*)`, `GalaxyDataManager`, `PartyManager`,
`CodexList`, `ActivePlayTimer`, `WorldMap*`, `Notifications*`, `LootContainer*`.

## No code references — and why that is expected

`tools/scan_xrefs.py` scanned `.text` (42 MB) for RIP-relative `lea`/`mov`/`cmp`
instructions targeting those addresses: **0 hits**.

The reason is visible in the PE layout: the strings live in `.rdata` and are referenced from
`typeinfo` RTTI records and vtables, not from code. `FBCHUNKS`/`FB\0SAVE\n` are compared as
32-bit immediates (the compiler folds the short magic constants), so they leave no data
reference either. Getting from a class name to a function therefore requires real RTTI →
vtable → virtual-call analysis, which is exactly the expensive pass that was stopped.

## What this means for the project

- The executable is **not** where plot-flag *names* live, so it is not on the critical path
  for the check catalogue. Names come from the game's data (see
  `docs/ASSET-NAMES.md`), and the missing join is GUID ↔ name inside compressed cas chunks.
- The exe becomes important again for the **live bridge** (v0.5 / v1): locating the plot
  manager to read/write flags in memory instead of on disk. That work should run Ghidra
  headless with `-analysisTimeoutPerFile` on a machine-time budget, or with the expensive
  analyzers disabled, and it should target the `WorldStateManager`/`PlotSaveGameAgent`
  vtables rather than string xrefs.

## Reproduce

```
python tools/scan_xrefs.py "C:\Steam\steamapps\common\Mass Effect Andromeda\MassEffectAndromeda.exe"
```

The script prints the PE sections, every anchor's virtual address, and any code xref it can
prove with a RIP-relative instruction.
