# The 38 galaxy-map systems, by name

`game/space/systems/<code>` is the internal id; the **name** comes from the system prefab's
`spaceobject_sun_<name>` import, and the **planets** are its `spaceobject_plt_*` imports
(`probe_galaxymap_prefab.py names`). Unnamed moons/asteroids (`gas_104`, `ice_111`, `lun_103`,
`des_104`, `met_103`, `ali_114`, `lav_111`) are omitted here.

Cross-checked against the owner's galaxy-map screenshot (2026-10-31): 12 of the 15 visible labels
match exactly (Onaon, Remav, Nol, Govorkam/Gavorkam, Hefena, Vaalon, Kindrax, Zaubray, Civki,
Faroang, Zheng He, Eriksson/Eiriksson). **Rohvir, Pytheas and Skeldah appear on the map but match no
sun asset** — they are the localized names of three systems whose internal star names are
placeholders (`c11`, `c12`, and one of the others), so those three cannot be named from the assets.

| id | name | named planets | landable | unlocked by |
| --- | --- | --- | --- | --- |
| aya_01 | **Onaon** | Aya hub, Maeraav | `ayaunc` (Aya) | post-MCM |
| aya_02 | Remav | Teroshe | — | post-Aya hub |
| aya_03 | Nol | Fenhajan | — | post-Aya hub |
| aya_04 | Sabeng | — | pas13 | post-Aya hub |
| aya_05 | **Tafeno** | Solad (+ Salarian ark) | — | kett flagship |
| aya_06 | Vaalon | Ejoda | — | post-Kadara |
| aya_07 | Valay | — | — | own system prefab |
| aya_08 | Togessan | Garef | — | post-M4 |
| aya_09 | Hefena | Dovar | — | post-Kadara |
| aya_10 | Joba | H-047c, Phaidra | pas04 | post-Kadara |
| aya_11 | Nalesh | Rahere | — | post-Aya hub |
| aya_12 | Inalaara | — | pas10, pas88 | own system prefab |
| aya_13 | Shojaon | Fenodam | — | post-M4 |
| kadara_01 | **Gavorkam** | Kadara hub, Mine | `kadaraunc` (Kadara) | post-Aya vault |
| kadara_02 | Zaubray | Elaaden, H-315 | — | post-Kadara |
| kadara_03 | Anasa | Acermos, Sedele | — | post-Kadara |
| kadara_04 | Solminae | Avelosa | — | post-Kadara |
| kadara_05 | Faross | Efaja | pas19 | post-M4 |
| kadara_06 | Kindrax | — | h073 | post-M4 |
| kadara_07 | Vaar | Maeshesa, Margoth | — | post-M5 |
| kadara_08 | Ratul | Govok's Folly | — | post-M5 |
| kadara_09 | Faroang | Farrum, Maearla | — | post-Aya hub |
| kadara_10 | **Civki** | — | — | remnant city (M5) |
| kadara_11 | c11 | — | — | post-M4 |
| kadara_12 | c12 | — | — | post-M5 |
| meridian_01 | **Saajor** | Meridian hub, Roha | — | Meridian (M7) |
| meridian_02 | Vaotessa | Fensayat | — | post-M5 |
| meridian_03 | Layan | — | pas29 | post-M5 |
| meridian_04 | Bosavay | Ishang | pas60 | post-M5 |
| nexus_01 | Eiriksson | Habitat 7 | — | default systems |
| nexus_02 | Ibn Majid | **Eos**, Nyota Penda | — | default systems |
| nexus_03 | Zheng He | — | — | own system prefab |
| nexus_04 | Pfeiffer | Korvath | — | default systems |
| nexus_05 | Tecunis | H-523c, Slohva | — | post-Kadara |
| nexus_06 | Meos | Vael | — | post-M5 |
| nexus_07 | Sephesa | H-1119, Kearnos II | — | own system prefab |
| nexus_08 | Darhegah | Denesh | — | post-M4 |
| nexus_09 | Jirayder | H-097b | — | post-Aya hub |

## What this means for a test

Only four systems carry a late unlock, and two of them are visible on a mid-game map:

| system | name | beat | on the 31 % screenshot |
| --- | --- | --- | --- |
| aya_01 | Onaon | post-MCM | **visible** (14 %) → already open |
| kadara_10 | Civki | remnant city (M5) | **visible** (66 %) → already open |
| aya_05 | Tafeno | kett flagship | not visible → **expected delta** |
| meridian_01 | Saajor | Meridian (M7) | not visible → **expected delta** |

So on the `Careerb191e387-0ManualSave` (after M5, before M7) save the mod should add exactly
**Tafeno** and **Saajor** to the selectable systems. If those two are still locked with the mod on,
`AvailableFlag` is not what the map reads and the next lever is the prefab spawn entry.

Venue reminders: Tafeno is the system with **Solad** and the **Salarian ark**; Saajor is the
**Meridian hub** system.
