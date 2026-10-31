"""Archipelago client for Mass Effect Andromeda.

The game has no live bridge yet, so this client watches the save folder: every time the game
writes a save, the plot flags are read and any newly satisfied check is sent to the server.
Items that arrive are queued to disk (and applied once item effects exist for them).

Goal detection is provisional: it fires when every check in the slot's goal region has been
reported. That becomes a single real flag once the Meridian completion flag is identified.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import Utils
from CommonClient import (ClientCommandProcessor, CommonContext, gui_enabled, logger,
                          server_loop)
from NetUtils import ClientStatus

from . import client_core

GAME_NAME = "Mass Effect Andromeda"
POLL_SECONDS = 5.0


class MEACommandProcessor(ClientCommandProcessor):
    def _cmd_status(self) -> bool:
        """Show what the client sees: bound career, checks sent, pending items."""
        ctx = self.ctx
        if not isinstance(ctx, MEAContext):
            return False
        logger.info(f"save folder : {client_core.SAVE_DIR}")
        logger.info(f"career      : {ctx.career_name or '(not bound yet)'}")
        logger.info(f"save file   : {ctx.last_path or '(none)'}")
        logger.info(f"detectors   : {len(ctx.detectors)}")
        logger.info(f"checks sent : {len(ctx.checked_locations)}")
        logger.info(f"items held  : {len(ctx.queue.unapplied) if ctx.queue else 0} unapplied")
        return True

    def _cmd_items(self) -> bool:
        """List received items that have not been granted in game yet."""
        ctx = self.ctx
        if not isinstance(ctx, MEAContext) or not ctx.queue:
            return False
        pending = ctx.queue.unapplied
        if not pending:
            logger.info("no pending items")
            return True
        for item in pending:
            logger.info(f"  {item.name} (from player {item.player})")
        return True


class MEAContext(CommonContext):
    game = GAME_NAME
    items_handling = 0b111
    want_slot_data = True
    command_processor = MEACommandProcessor

    def __init__(self, server_address: str | None, password: str | None) -> None:
        super().__init__(server_address, password)
        self.detectors: list[client_core.Detector] = []
        self.tracker: client_core.CheckTracker | None = None
        self.map_tracker = client_core.WorldMapTracker()
        self.queue: client_core.DeliveryQueue | None = None
        self.last_path: Path | None = None
        self.career_name: str = ""
        self.last_level: str = ""
        self.finished_game = False
        self.slot_data: dict[str, Any] = {}
        self.watch_task: asyncio.Task | None = None

    # -- AP plumbing -------------------------------------------------------
    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect(game=GAME_NAME)

    def on_package(self, cmd: str, args: dict[str, Any]) -> None:
        if cmd != "Connected":
            return
        slot_data = args.get("slot_data") or {}
        self.slot_data = slot_data
        self.detectors = client_core.detectors_from_slot_data(slot_data)
        self.tracker = client_core.CheckTracker(self.detectors)
        appdata = Path(Utils.user_path("MassEffectAPSetup") if hasattr(Utils, "user_path")
                       else Path.home() / "AppData" / "Local" / "MassEffectAPSetup")
        self.queue = client_core.DeliveryQueue(appdata / "MEA" / "pending-items.json")
        logger.info(f"{len(self.detectors)} check detectors loaded from slot data")
        if self.watch_task is None or self.watch_task.done():
            self.watch_task = asyncio.create_task(self.watch_saves(), name="MEA save watcher")

    # -- the actual client -------------------------------------------------
    def _goal_reached(self) -> bool:
        goal = (self.slot_data or {}).get("goal") or {}
        if goal.get("kind") == "level":
            return self.last_level in set(goal.get("levels") or [])
        if goal.get("kind") != "region":
            return False
        region = goal.get("region")
        in_region = [d for d in self.detectors if d.region == region]
        if not in_region:
            return False
        return all(d.location_id in self.checked_locations for d in in_region)

    async def handle_save(self, path: Path) -> None:
        try:
            state = client_core.CareerState.read(path)
        except Exception as exc:  # noqa: BLE001 - a half-written save must not kill the client
            logger.debug(f"could not read {path.name}: {exc}")
            return
        if not self.career_name:
            self.career_name = state.save_name
            logger.info(f"bound to career {state.save_name!r} ({path.name})")
        self.last_level = state.level
        new = self.tracker.poll(state)
        map_new = self.map_tracker.poll(state)
        for key in map_new[:5]:
            logger.info(f"new galaxy-map location: {self.map_tracker.label(key)}")
        if len(map_new) > 5:
            logger.info(f"... and {len(map_new) - 5} more galaxy-map locations")
        if new:
            self.checked_locations.update(d.location_id for d in new)
            await self.send_msgs([{"cmd": "LocationChecks",
                                   "locations": [d.location_id for d in new]}])
            for det in new[:5]:
                logger.info(f"check: {det.name}")
            if len(new) > 5:
                logger.info(f"... and {len(new) - 5} more")
        if not self.finished_game and self._goal_reached():
            await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            self.finished_game = True
            logger.info("goal reached: Meridian checks complete")

    async def watch_saves(self) -> None:
        while not self.exit_event.is_set():
            try:
                path = client_core.latest_save()
                if path is not None:
                    stat = path.stat()
                    signature = (path, stat.st_mtime, stat.st_size)
                    if getattr(self, "_last_signature", None) != signature:
                        self._last_signature = signature
                        self.last_path = path
                        await self.handle_save(path)
                if self.queue is not None:
                    while self.items_received and len(self.queue.items) < len(self.items_received):
                        item = self.items_received[len(self.queue.items)]
                        self.queue.add(item.item, self.item_names.lookup_in_slot(item.item, item.player),
                                       item.player)
                        logger.info(f"queued item: {self.queue.items[-1].name}")
            except Exception as exc:  # noqa: BLE001 - keep watching
                logger.debug(f"watcher error: {exc}")
            await asyncio.sleep(POLL_SECONDS)

    def make_gui(self):
        return None


def launch(*args: str) -> None:
    async def main() -> None:
        ctx = MEAContext(args[0] if args else None, None)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        await ctx.exit_event.wait()
        ctx.server_task.cancel()
        if ctx.watch_task:
            ctx.watch_task.cancel()

    Utils.init_logging("MassEffectAndromedaClient", exception_logger="Client")
    import colorama
    colorama.just_fix_windows_console()
    asyncio.run(main())
    colorama.deinit()
