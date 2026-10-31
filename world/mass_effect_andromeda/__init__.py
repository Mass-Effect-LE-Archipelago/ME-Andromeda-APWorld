from worlds.LauncherComponents import Component, Type, components, launch as launch_component

from .world import MassEffectAndromedaWorld as MassEffectAndromedaWorld


def launch_client(*args: str) -> None:
    from .client import launch
    launch_component(launch, name="MassEffectAndromedaClient", args=args)


components.append(Component(
    "Mass Effect Andromeda Client",
    func=launch_client,
    component_type=Type.CLIENT,
    game_name="Mass Effect Andromeda",
    supports_uri=True,
    description="Watches the Mass Effect Andromeda save folder and reports checks to the multiworld.",
))
