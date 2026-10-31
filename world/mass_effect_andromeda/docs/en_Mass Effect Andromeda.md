# Mass Effect Andromeda

A randomizer for the Andromeda campaign. You start on the **Tempest** with the **Nexus** and one
starting destination open. Everything else — planets, priority operations, squadmates, weapons —
is scattered across the multiworld.

## What counts as a check

The game stores its plot state in the save file as GUID-keyed flags. The world reads the flags
that the game itself names through its assets — plot expressions, journal graphs, conversation
lines, galaxy-map destinations and story triggers — and turns **5,722** of them into checks:

| region | checks | region | checks |
| --- | --- | --- | --- |
| Global | 1,478 | Meridian | 182 |
| Nexus | 721 | Havarl | 126 |
| Kadara | 489 | Kett Flagship | 78 |
| Space | 460 | Vault | 52 |
| Eos | 394 | Outposts | 47 |
| Voeld | 341 | Squadmates (6) | 158 |
| Elaaden | 314 | Crew (4) | 74 |
| Tempest | 282 | Colonial Life | 20 |
| Loyalty Missions | 250 | Exaltation Facility | 18 |
| Aya | 216 | Main Plot / Pathfinder / Hyperion | 28 |

Checks are objective-style: quest gates, "available" markers, counters, outpost states, trust
levels, and banter/conversation lines heard (`ConversationLine.OccurrencePlotFlagId`). Names come
from the game's own asset paths. Level-scaffolding flags (`zzdebug`, `mainflow`, streaming
triggers) are filtered out on purpose.

## Items

- **Access**: `Eos Access`, `Voeld Access`, `Havarl Access`, `Kadara Access`, `Elaaden Access`,
  `H-047c Access`, `Meridian Access`, `Nexus Access`, `Aya Access`
- **Priority operations**: `Priority Op: A Better Beginning`, `The First Vault`, `Exaltation`,
  `Kett Flagship`, `Remnant City`, `Meridian`
- **Weapons**: 23 weapon unlocks (Carnifex, Valkyrie, Black Widow, …)
- Filler: research data, credits, resources

## Goal

Complete **Meridian**: reach the Meridian region and hold `Priority Op: Meridian`. The victory
event sits on the Meridian finale.
