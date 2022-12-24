from abc import ABC, ABCMeta, abstractmethod
from typing import Self
import discord
from discord import ui
from discord.ext import bridge, commands
from loguru import logger


class CogABCMeta(discord.cog.CogMeta, ABCMeta):
    pass


class MusicCogABC(ABC, commands.Cog, metaclass=CogABCMeta):

    _client: bridge.Bot

    @property
    def client(self) -> bridge.Bot:
        return MusicCogABC._client

    async def invoke_command(self, ctx: bridge.BridgeExtContext, name: str):
        command = self._client.get_command(name)
        if not command:
            return

        if _ := not command.enabled:
            command.enabled = True
        try:
            await command.invoke(ctx)
        except commands.CommandOnCooldown:
            await ctx.send("You are on cooldown", delete_after=3)
        if _:
            command.enabled = False


class ViewABC(ABC, ui.View):

    _client: bridge.Bot

    @property
    def client(self) -> bridge.Bot:
        return ViewABC._client

    @classmethod
    @abstractmethod
    def from_message(cls, child_cls, message: discord.Message) -> Self:  # type: ignore
        base_view = super().from_message(message, timeout=None)
        cls.__view_children_items__ = []
        return child_cls(*base_view.children)


class HandlerABC(ABC):

    _client: bridge.Bot

    @property
    def client(self):
        return HandlerABC._client


class ThreadHandlerABC(HandlerABC, ABC):
    def __init__(self, thread: discord.Thread | None):
        self.__thread = thread

    @property
    def thread(self):
        return self.__thread

    @staticmethod
    async def get_thread_message(thread: discord.Thread) -> discord.Message | None:
        try:
            return (await thread.history(limit=1, oldest_first=True).flatten())[0]
        except Exception as e:
            logger.warning("NO THREAD MESSAGE FOR U @", e)
            return None

    async def update_thread_views(self):
        raise NotImplementedError
