# Mass Effect Andromeda — setup

This world is in development. The Archipelago side works (seed generation, items, checks and
logic); the game side is a save-file client that is not shipped yet.

## Generating a seed

1. Put `mass_effect_andromeda.apworld` in `custom_worlds/` (or the folder under `worlds/`).
2. Create a player YAML:

```yaml
name: Ryder
game: Mass Effect Andromeda
Mass Effect Andromeda:
  starting_region: eos
  weapon_items: true
  bool_checks_only: false
```

3. Generate as usual.

## Playing

The Archipelago client watches the save folder
(`Documents\BioWare\Mass Effect Andromeda\Save`): when the game writes a save, newly satisfied
plot flags are sent as checks. Items that arrive are queued to
`%LOCALAPPDATA%\MassEffectAPSetup\MEA\pending-items.json`.

**Items are not granted in game yet.** The delivery mechanism is built and tested, but the
item → flag table is still being worked out, so for now the client tracks the seed and records
what you received. Start a **new Ryder** after installing the world so checks begin near zero.
