# Client: save-watching, checks and item queue

`world/mass_effect_andromeda/client.py` is the Archipelago client; `client_core.py` holds the
logic and is testable without Archipelago (see `test/test_client_core.py`).

## How it works

The game has no live bridge yet, so the client watches the save folder
(`Documents\BioWare\Mass Effect Andromeda\Save`) and reads the newest `Career*` file whenever its
modification time or size changes:

1. **Bind** — first save seen defines the career; `GalaxyDataStateManager`/plot data is read.
2. **Detect** — detectors come from the seed's `slot_data` (one per location: id, name, guid,
   kind, region).
3. **Send** — newly satisfied locations are sent as `LocationChecks`, each once.
4. **Receive** — items are queued to `%LOCALAPPDATA%\MassEffectAPSetup\MEA\pending-items.json`
   so a restart never loses them.

Detection rules (heuristics, documented because they are not all equally strong):

| kind | rule |
| --- | --- |
| bool | the flag is true |
| int | the value differs from the value captured at bind time |

Float flags are not offered as locations at all: there is no stable "done" semantics for a float,
so such a location could never be checked (`tools/build_checks.py` drops them).

At bind, already-satisfied detectors are reported too: a fresh career legitimately has a few
flags set, and re-sending an already-checked location is harmless.

**Goal (provisional):** the client sends `CLIENT_GOAL` when every check in the slot's goal
region has been reported. That becomes a single real flag once the Meridian completion flag is
identified from an early save.

## Test evidence (offline, on the owner's two saves)

```
slot data: 1432 detectors rebuilt
bind on the 87% save: 64 checks already satisfied
moving to the 99.5% save: 127 new checks
  e.g. Aya: Aya Tsk Nexexch Goodresultfollowup, Aya: Hub Aya Sqd Cora Banter1eligible, …
delivery queue: persisted and reloaded correctly
ALL CLIENT CORE TESTS PASSED
```

Re-polling the same save reports nothing twice, and the same location is never sent twice.
The client module imports cleanly inside Archipelago 0.6.9 (`client module ok: Mass Effect
Andromeda`).

## What the client cannot do yet

- **Grant items in game.** The delivery *mechanism* is built and proven
  (`tools/apply_effects.py`: N flag writes in one rewrite, backup, verification that only the
  requested flags changed and the file size is unchanged). What is missing is the item → flag
  table, and two plausible sources were ruled out: every weapon research project shares the same
  `CompletedFlag`/`BoolProvider` flag (so weapons are not addressable), and the player's
  inventory/crafting state lives in the component-container section of the save, which is not
  decoded yet.
- **Read live state.** Saves are written at save points (autosave + manual), so checks appear
  with a delay and a crash can lose progress since the last save. A DLL bridge later removes
  both limits.
- **Bind to a specific career.** It always follows the newest save in the folder. Switching
  saves mid-seed would need an explicit `/bind <file>` command.
