from typing import Optional, Type

import discord
from discord import ui
from discord.ext import bridge  # type: ignore
from loguru import logger

from abcs import HandlerABC, ThreadHandlerABC
from enums import SearchPlatform, ThreadType
from Music_cog import Utils  # type: ignore

from .message_config import conf  # type: ignore
from .Views import MainView, SettingsView, setup_view_client  # type: ignore


def setup(client: bridge.Bot):
    setup_view_client(client)
    HandlerABC._client = client


class MainMessageHandler(HandlerABC):
    def __init__(self):
        self.__message: Optional[discord.Message] = None

    @property
    def message(self):
        return self.__message
    
    @property
    def looping(self):
        return MainView.from_message(self.__message).looping
    
    @property
    def shuffle(self):
        return MainView.from_message(self.__message).shuffle
        
    @classmethod
    async def with_message(cls, room: discord.TextChannel) -> "MainMessageHandler":
        handler = cls()
        handler.__message = await cls.get_main_message(room)
        return handler

    @staticmethod
    async def get_main_message(room: discord.TextChannel) -> Optional[discord.Message]:
        try:
            async for message in room.history(limit=3, oldest_first=True):
                if len(message.embeds) > 0:
                    return message  # type: ignore
        except Exception as e:
            logger.error(f"NO MAIN MESSAGE - {e}")
        return None

    @staticmethod
    def create_main_view() -> MainView:
        return MainView()

    async def update_main_view(self):
        self.client.add_view(
            MainView(),
            message_id=self.message.id,
        )

    @staticmethod
    def create_file(
        path: str = "Music_cog/room/other_files/banner.gif",
        name: str = "Banner.gif",
    ) -> discord.File:
        return discord.File(open(path, "rb"), filename=name)

    @staticmethod
    def create_embed(settings: dict = None) -> discord.Embed:
        if settings is None:
            settings = {
                "title": "Queue is clear",
                "type": "video",
                "color": 0x00FF00,
                "footer": {
                    "text": "Type the music name",
                    "icon_url": conf["back_image"],
                },
                "image": {"url": conf["back_image"]},
            }

        embed = discord.Embed.from_dict(settings)
        return embed

    async def update_embed(self, track=None):
        settings = None
        if track is not None:
            settings = {
                "title": track.title,
                "type": "video",
                "color": 0x00FF00,
                "url": track.track_url,
                "author": {"name": track.artist, "url": track.artist_url},
                "footer": {
                    "text": "Playing",
                    "icon_url": track.thumbnail
                    if track.thumbnail
                    else conf["back_image"],
                },
                "image": {"url": track.thumbnail},
            }
        new_embed = self.create_embed(settings)
        await self.message.edit(embed=new_embed)


class SettingsThreadHandler(ThreadHandlerABC):
    @property
    async def search_platform(self) -> SearchPlatform:
        thread_message: discord.Message = await self.get_thread_message(self.thread)  # type: ignore
        view: SettingsView = SettingsView.from_message(thread_message)
        return view.search_platform  # type: ignore

    @staticmethod
    def create_settings_view() -> SettingsView:
        return SettingsView()

    async def update_thread_views(self):
        thread_message = await self.get_thread_message(self.thread)
        self.client.add_view(
            SettingsView(),
            message_id=thread_message.id,
        )


class ThreadsHandler:

    SettingsThreadHandler = SettingsThreadHandler

    @staticmethod
    async def update_threads_views(guild: discord.Guild):
        for thread_type in ThreadType:
            match thread_type:
                case ThreadType.SETTINGS:
                    await SettingsThreadHandler(
                        Utils.get_thread(guild, thread_type)  # type: ignore
                    ).update_thread_views()
