# Where a "galaxy map open" mod would act

Dumped and parsed a real destination asset (`game/space/destinations/plt/destination_plt_eos`,
partition GUID `70775536-…`, object `GalaxyObjectData`, 29 fields):

| field | value | why it matters |
| --- | --- | --- |
| `CurrentDestinationFlag` | flag `d2392298-…` | per-destination plot flag the game reads |
| `ScannedFlag` | flag `ff9c0966-…` | "scanned/discovered" state |
| `IncludeInCompletion` | `ConditionSchematic` import `e60d7471-…` | **a condition asset decides inclusion** |
| `ExcludeFromJournalTask` | `ConditionSchematic: None` | same mechanism, unused here |
| `Anomalies[]` | list of `PlotFlagId` | POI gating |
| `LevelNameHash` | `4234508223` | the level it loads |
| `DestinationID` | `0` | ordering/index |

The presence of `ConditionSchematic` is the important find: Frostbite assets here don't just carry
flags, they **import condition-logic assets** (`ConditionLogicPrefabBlueprint`, 2,258 references in
the flag census). That is the layer where "may the player fly here" lives — and it is editable,
because we can now read, modify and rebuild every container on the path to it:

```
.fbmod metadata   → byte-identical round-trip (13/13)
.archive chunks   → parse, edit, rebuild (verified on the 2.4 MB pack)
EBX partitions    → read (this dump); dump → Partition → field listing works
```

## What to check next

1. Dump the `ConditionSchematic` asset `e60d7471-…` and see whether it is a simple
   flag rule ("available when flag X") or a shared logic tree. A shared tree is dangerous to edit
   (it likely gates many destinations at once).
2. Dump a **system** asset (`game/space/systems/...`) — availability may be set one level up.
3. Compare the Eos destination against one that is *not* reachable early (e.g. Kadara) to see which
   field differs — that difference is the gating lever, and it is a field-level diff on assets we
   can already read and write.

## Results of those three checks (same session)

**(3) Destination field diff — no availability lever.** Eos vs Kadara (`destination_plt_eos`
vs `destination_plt_kadarahub`, both 29 fields): the only differences are content fields —
`Name`, `CodexHash`, `Difficulty`, `LevelNameHash`, `ObjectCategory`, `ObjectDisplayName`,
`ScannedFlag`, `Metals`. `IncludeInCompletion` / `ExcludeFromJournalTask` are identical. So the
destination asset does **not** encode whether the player may travel there.

**(2) System asset — it is a logic prefab, not a data row.** `game/space/systems/kadara_01`
(partition `94cc6b54-…`) is a `PrefabBlueprint` whose interesting content is
`PropertyConnections`, `LinkConnections`, `EventConnections`, `Objects` and `Interface` — i.e. a
**logic graph**. Nothing like `UnlockFlag` / `Available` exists.

**Conclusion:** the galaxy map opens systems through a logic graph evaluated at runtime, matching
the earlier save-side finding (availability follows quest state, not flags). A gating mod is
therefore a *logic-graph* edit, which our container tooling can carry but which is a materially
bigger job than flipping a field — and a risky one, since these graphs are shared.

That is the honest cost estimate for "open the map from the start": containers solved, content
identified as logic graphs, editing still ahead.

## Graph work started: destination locators

System graphs contain `SystemDestinationLocatorEntityData` nodes (Aya 2, Kadara 4). Their fields:

| field | aya_01 | kadara_01 |
| --- | --- | --- |
| `Visible` | True | True |
| `State` | 0 | 0 |
| `CanFastTravel` | False | — |
| `FuelCost` | 1 | — |
| `JumpToSystem` | import `a668f233…`, `e207ddf3…` | `e137ca53…`, `a83fbd59…`, `bc4b8e86…`, `17d09122…` |
| `DisplayCondition` / `HideCondition` | `PlotFlagReference` → **zero GUID**, `DesiredValue: True` | same |

So every locator already reads "visible" and its conditions reference the **null flag**
(`00000000-…`) — i.e. the condition slot is unused in both an open and a late system. That means
the locator itself is not where a system is gated either, and the gate is one level up again: in
the galaxy-map asset that lists which systems are jumpable, or in the quest data that mutates it.

Next (fresh session, see `HANDOFF.md` §7): find the galaxy-map asset that owns the system list —
search `game/space/` for assets with many `JumpToSystem` imports, or walk `PropertyConnections` in
the `PrefabBlueprint` from the system root.

## FOUND: the galaxy-map owner, and what its 38 conditions really are

`game/ui/pausemenu/galaxymap/prefabs/spawnedgalaxymap` (partition `e9d830c0-8980-11e5-b9be-d95347869af1`)
references **all six** jump GUIDs; no other asset outside `game/space` references more than one.
94 objects: 42 `SpatialReferenceObjectData`, 38 `PlotConditionNotificationEntityData`, plus a
`PrefabBlueprint` with 243 property / 77 link / 116 event connections and 92 spawned objects.

All 38 condition objects have `TriggerOnValueChange: True`, `CheckOnStart: False`, and a
`PlotConditions[]` entry of a **real plot flag** with `DesiredValue: True`. Their state:

| save | flags true | flags present |
| --- | --- | --- |
| fresh `M0` | 0/38 | **0** |
| `M1` | 0/38 | **0** |
| 87 % | 0/38 | 38 |
| 99.5 % | 0/38 | 38 |

So these are **one-shot reveal notifications**: the flag is allocated when a system is first
discovered, flipped true to fire the "new system" notification, and left false afterwards. They are
absent entirely from a fresh career.

**Consequence (answers the save-side question definitively):** planet access cannot be delivered by
editing a save. A fresh save does not contain these flags, and our writer edits existing flags only
— inserting new flag-table entries is a different, unsolved job. The lever is game-side: a mod that
fires the notification (or bypasses the gate) at load.

### Follow-up: the 38 GUIDs are `SystemData.AvailableFlag`, not just notification triggers

Same session, one level deeper — full write-up in **`docs/GALAXYMAP-GATE.md`**.

`spawnedgalaxymap` imports **38 `game/space/systems/systemdata/systemdata_<system>` rows**, and each
row is an 848–864-byte `SystemData` (base `GalaxyObjectData`) with exactly:

```
AvailableFlag  -> PlotFlagId   (the per-system availability slot)
VisitedFlag    -> PlotFlagId
```

The prefab's 38 condition objects watch **exactly** those 38 `AvailableFlag` values (set equality
verified, no extras), so the "notification" reading and the "availability field" reading are the
same facts seen from two ends. The flags are written by ten
`game/plots/systems/space/galaxymap_unlock_*` plot assets: 34 of 38 systems are covered
(`defaultsystems`, `postayahub`, `postayavault`, `postkadara`, `postm4`, `postm5`, `postmcm`,
`meridian`, `remnantcity`, `kettflagship`); `aya_07`, `aya_12`, `nexus_03`, `nexus_07` are gated
inside their own system `PrefabBlueprint`.

Tested against all 32 career saves: **0/38 true** in every one, including the finished career where
all 38 are present-but-false. So the field is either consumed when read or not the persistent store
— which is precisely why the mod should swap it for `alwaystrue`
(`bf899768-3614-11e5-aa63-b2e3b7222cc5`) rather than for a normal true flag: a real flag can be
written back to false by the plot system, a constant cannot. Pre-flight on all 38 rows: the GUID
occurs once per partition, the swap preserves length, and every patched partition reparses.

The `JumpToSystem` graph is also complete (80 edges across 38 systems, 0 unresolved, every system
has an inbound edge), so availability is the only thing standing between the player and the map.



