from abc import ABC, ABCMeta, abstractmethod
from typing import Self

import Bot
import discord
from discord import ui
from discord.ext import bridge, commands


class CogABCMeta(discord.cog.CogMeta, ABCMeta):
    pass


class MusicCogABC(ABC, commands.Cog, metaclass=CogABCMeta):
    _client: Bot.TenB_Bot

    @property
    def client(self) -> Bot.TenB_Bot:
        return MusicCogABC._client

    async def invoke_command(
        self,
        ctx: discord.ApplicationContext | bridge.BridgeExtContext | bridge.BridgeApplicationContext,
        name: str,
        /,
        *args,
        **kwargs,
    ):
        command: bridge.BridgeExtCommand = self._client.get_command(name)  # type: ignore
        if not command:
            return

        if _ := not command.enabled:
            command.enabled = True
        try:
            for check in command.checks:
                check(ctx)  # type: ignore

            if command._before_invoke:
                await command._before_invoke(self, ctx)  # type: ignore

            await command(ctx, *args, **kwargs)  # type: ignore

            if command._after_invoke:
                await command._after_invoke(self, ctx)  # type: ignore
        except commands.CommandOnCooldown:
            await ctx.send("You are on cooldown", delete_after=3)
        if _:
            command.enabled = False


class ViewABC(ABC, ui.View):
    _client: Bot.TenB_Bot
    __view_children_items__ = []

    @property
    def client(self) -> Bot.TenB_Bot:
        return ViewABC._client

    @classmethod
    @abstractmethod
    def from_message(cls, message: discord.Message, /, *, timeout: float | None = None) -> Self:
        view = cls(timeout=timeout)
        view.clear_items()
        for component in ui.view._walk_all_components(message.components):
            view.add_item(ui.view._component_to_item(component))
        view.message = message
        return view
        # base_view = super().from_message(message, timeout=timeout)
        # view = cls(timeout=timeout)
        # view.clear_items()
        # for item in base_view.children:
        #     view.add_item(item)
        # return view


class HandlerABC(ABC):
    _client: Bot.TenB_Bot

    @property
    def client(self):
        return HandlerABC._client


class ThreadHandlerABC(HandlerABC, ABC):
    def __init__(self, thread: discord.Thread) -> None:
        self.__thread = thread

    @property
    def thread(self):
        return self.__thread
