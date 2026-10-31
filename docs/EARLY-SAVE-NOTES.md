# Early-save findings (real fresh career, 2026-10-31)

First genuine early-game data: a new career `c8fa1bc8`, saved through the prologue and into M1.

| save | timestamp | plot flags | location tag |
| --- | --- | --- | --- |
| `Careerc8fa1bc8-Chapter0` | 03:51:21 | 298 | `SavedGame_M0` |
| `Careerc8fa1bc8-0AutoSave` | 04:00:42 | 443 | `SavedGame_M0` |
| `Careerc8fa1bc8-1AutoSave` | 04:04:02 | 760 | `SavedGame_M0` |
| `Careerc8fa1bc8-2AutoSave` | 04:05:54 | 778 | `SavedGame_M0` |
| `Careerc8fa1bc8-Chapter1` | 04:08:55 | 1,032 | `SavedGame_M1` |
| `Careerc8fa1bc8-Mission` | 04:10:45 | 1,118 | `SavedGame_M1` |

Compare with the finished saves: 70,259 and 78,235 flags. **A fresh career starts with ~300 plot
flags**, so almost the entire flag table is created by playing.

## The client works on real early-game data

`client_core` bound to `Chapter0` reports **5** already-satisfied checks (a new career is nearly
empty, as hoped), then reports progress as the saves advance:

```
bind on Chapter0      5 checks
0AutoSave   335 bools -> 11 new   (Global: Squad Agm/Asa/Hmf Recruited)
2AutoSave   656 bools ->  8 new   (Intrld 0400 Nexus Meet Leaders, Nexus tram)
Chapter1    871 bools ->  0 new
Mission     956 bools ->  5 new   (Meridian: Mako Landing …)
```

This is the first end-to-end evidence of check detection on a genuine playthrough, not a
synthetic pair.

## Planet availability is **not** in plot flags

The prologue → Eos boundary (`2AutoSave` → `Chapter1`) flips **200** flags, and **none of them is
named by any asset** — they are runtime-allocated GUIDs. Supporting evidence:

- the galaxy agent (`GalaxyDataStateManager`) stores only the player's *current* system and
  destination: zero in the early save, set in the finished one. There is no unlock list.
- every landing-gate asset (`landingcomplete_plt_*`) references the *same* shared "exit
  docking/landing ready" flag, plus transient markers that reset.
- the destination assets' `ScannedFlag`s are false even in the 99.5 % save.

Conclusion: the galaxy map computes availability at runtime from quest/journal state, which lives
in the `JournalSystem` agent, not in the plot block. **Planet access cannot be granted or revoked
by editing plot flags.**

## What this means for the randomizer

Three options, in order of fidelity:

1. **AP mod makes the map open** — a Frosty mod (our own, applied by our mod manager) removes the
   story gating so every planet can be flown to from the start; progression logic then decides
   what is *allowed*, and the player follows the item order. This is what most heavily-gated games
   do and it is the only option that survives a shuffled item order without softlocks.
2. **Honour system** — no game change: the client shows which planets are open, the player
   self-restricts. Cheapest, and what the current build implies, but a player can break the seed
   by flying somewhere early.
3. **Journal-state editing** — deliver mission state directly; needs the `JournalSystem` agent
   decoded and is the largest of the three.

Option 1 keeps the item list meaningful and uses the mod manager we already built.

## The profile files hold no progression

`Save\ProfOpts` is an `FBCHUNKS` container like a save (1.5 MB, CRCs valid) but its payload is a
settings store: `textLanguage`, `EnableRumble`, `IsFemalePathfinder`, `EnableTelemetry`,
`tutorialsActive`, `AutoLevelUp`, `ToggleAim`, `AutoWeaponSwap`, `CameraAutomaticShoulderSwap`,
`ShowDialogTones`, `EnableAimAssist`, `ToggleSprint`, `questTrackerActive`, `TogglePowers`,
`PlayerHelmetVisibility`, plus a default name ("scott"). `ProfOpts_profile` (and
`ProfOpts_204664383_profile`) are GStreamer audio settings text, not game data.

So there is no profile-level item unlock to exploit either: weapons, gear and planet access are
all in places we cannot write meaningfully yet.

