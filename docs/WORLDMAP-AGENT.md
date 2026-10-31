# The world map agent is the galaxy discovery store

Agent **idx 2, `WorldMapSaveGameAgent`** (hash `0xED46AE0D`, version 4) holds the player's
world-map entries. This corrects an earlier conclusion: the *galaxy* agent (idx 4) only tracks the
current system/destination, but idx 2 does hold map/discovery state.

## Structure (decoded and verified)

```
u16 count                                    # entries in list 1
repeat count:
    frame24 {                                # bit length
        bytes[16]  location GUID
        u16        inner count
        …inner records (not decoded yet)…
    }
# when the agent version >= 4, a second list follows with the same shape
u16 count2
repeat count2: frame24 { bytes[16] GUID, u16 inner count, … }
```

Decoder: `tools/probe_worldmap.py` (works on every save in the folder).

## It grows with story progress — exactly like planet access should

| save | location |
| --- | --- |
| `Careerc8fa1bc8-Chapter0` | `SavedGame_M0` — **1** entry |
| `Careerc8fa1bc8-2AutoSave` | `SavedGame_M0` — **3** entries |
| `Careerc8fa1bc8-Mission` | `SavedGame_M1` — **4** entries |
| `Career870ee94-1ManualSave` | finished — **33** entries |

The full-playthrough career (`b191e387`) gives the intermediate points, so the *moment* each entry
appears can be bracketed to a chapter (M1 → Nexus → M2 → Aya → M3 → Kadara → M4 → M5 → M7 →
Meridian → Eos).

## What is still unknown

The 16-byte GUIDs are **not** partition GUIDs of known assets (0 of 33 match `partition_guid` in
the joins), and they are not plot-flag GUIDs. A raw byte scan of all **2,041 `game/space/**`
partitions** for the 33 keys found **zero** occurrences (`tools/probe_worldmap_names.py`), so the
entries are not defined or referenced as literal bytes in the space assets either — they are
runtime keys, like the dynamically allocated plot flags seen at the M0 → M1 boundary.

That means the world map agent can still be used as a **signal** (entry count and the set of keys
change per planet) without knowing what each key is called: the client can record which keys exist
at bind time and report newly appearing ones. Naming them needs a different route (the galaxy map
UI/AI assets, or a memory-side comparison with Frosty loaded).


## Key counts across a full playthrough (`tools/name_worldmap_keys.py`)

| step | location | keys | new |
| --- | --- | --- | --- |
| Chapter0 | `SavedGame_M0` | 26 | 26 |
| Chapter1 | `SavedGame_M1` | 26 | 0 |
| Chapter51 | `HUB_Nexus` | 26 | 0 |
| Chapter30 | `M2` | 26 | 0 |
| Chapter4 | `HUB_Aya` | 26 | 0 |
| Chapter31 | `M3` | 26 | 0 |
| Chapter6 | `HUB_Kadara` | 28 | 2 |
| Chapter53 | `M4` | 32 | 4 |
| Chapter33 | `M5` | 36 | 4 |
| 0ManualSave | `HUB_Tempest` | 36 | 0 |
| Chapter34 | `M7` | 36 | 0 |
| Chapter10 | `HUB_Meridian` | 44 | 8 |
| Mission | `UNC_Eos` | 44 | 0 |

Keys only ever appear (never disappear), and new ones arrive exactly at Kadara, M4, M5 and the
Meridian arc — so this really is discovery state.

**Resolved:** the decoder is correct (both lists always mirror each other — 1+1, 4+4, 13+13 — and
the last key `2dab95f2-…` is shared by both careers, so the locations are global, not per-career).
The difference is playthrough state, not parsing: `b191e387`'s `SavedGame_M0` save simply has 13
discovered locations against 1 for `c8fa1bc8`'s. Baselines are therefore only meaningful relative
to the save a seed starts from — which is exactly what a bind-time baseline gives the client, so
key tracking can be wired in safely (`tools/probe_worldmap_baseline.py`).

## Can the planet order be derived from the ladder? Only partly

`tools/probe_step_regions.py` counts the *named* checks that appear at each step. The signal is
too sparse to identify the planet a step takes place on:

```
SavedGame_M1            +567 flags, 14 named -> Global 7, Nexus 4, Meridian 2
SavedGame_HUB_Nexus     +723 flags, 15 named -> Meridian 10, Global 3, Eos 1
SavedGame_M2           +3200 flags, 55 named -> Space 9, Nexus 7, Eos 6
SavedGame_HUB_Aya      +2464 flags, 13 named -> Aya 5, Space 4
SavedGame_M3           +2981 flags,  4 named -> Global 2, Meridian 1
SavedGame_HUB_Kadara   +2111 flags,  2 named -> Global 2
```

Only the hub steps are self-identifying (their location tag names them). The mission steps
(`M1`, `M2`, `M3`, `M4`, `M5`, `M7`) carry almost no named evidence about *where* they happen.

The world map keys are the better source: they appear at Kadara (+1), M4 (+2), M5 (+2) and the
Meridian arc (+4). That gives five steps a reliable "something new was discovered here" label, but
not a name for the location — so a **planet-by-planet chain cannot be built from the current
evidence**, and the world keeps its access-item gating (honour system in game) rather than
pretending to enforce an order the game does not follow.

Naming those keys is therefore the single unlock for both per-planet checks and an ordered chain.


`tools/progression_ladder.py` writes `docs/PROGRESSION-LADDER.md`: 14 saves in game order, with the
named flags that flip at every boundary (567 flips M0→M1, 723 M1→Nexus, …). The named flips are
mostly dialogue `*.perf` flags, which is why the structural state had to come from the agent.
