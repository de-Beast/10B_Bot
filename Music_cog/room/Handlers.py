import datetime
import random
from typing import Any, Optional, Union

import discord
from discord import ui
from discord.ext import bridge  # type: ignore
from loguru import logger

from abcs import HandlerABC, ThreadHandlerABC
from enums import SearchPlatform, ThreadType
from Music_cog import Utils  # type: ignore
from Music_cog.player.Track import Track

from .message_config import conf  # type: ignore
from .Views import MainView, SettingsView, setup_view_client  # type: ignore


def rofl(requester: Union[discord.User, discord.Member]) -> str:
    rofl_str = " – "
    match requester.id:
        case 447849746586140672:
            rofl_str = random.choice(
                (
                    "ПОПУЩЕНЕЦ",
                    "ОБСОСИК",
                    "БЕРСЕРК ГАВНИЩЕ ЕБУЧЕЕ"
                )
            )
        case 446753575465385998:
            rofl_str += random.choice(
                (
                    "ВОТ БЫ ТЫ НЕ РАЗГОВАРИВАЛ",
                    "ЖИРНОЕ ЧМО",
                    "КАКАЯ ЖЕ НАСТЕНЬКА ОХУИТЕЛЬНАЯ",
                )
            )
        case 309011989286354944:
            rofl_str += random.choice(
                (
                    "МОЯ СЛАДЕНЬКАЯ БУЛОЧКА",
                    "АНИМЕШНИК",
                    "ТРАХНИ МЕНЯ"
                )
            )
        case 600361186495692801:
            rofl_str += random.choice(
                (
                    "ЛУЧШИЙ В МИРЕ",
                    "СПАСИБО ЗА БОТА",
                    "АПНУЛ ВТОРУЮ ПЛАТИНУ"
                )
            )
    return rofl_str


def setup(client: bridge.Bot):
    setup_view_client(client)
    HandlerABC._client = client


def create_default_embed_properties(guild: discord.Guild) -> dict:
    properties: dict[str, Any] = {}
    footer = {"text": "prefix: ++"}
    description = "|"
    for thread_type in ThreadType:
        thread = Utils.get_thread(guild, thread_type)
        description += (
            f" [{thread_type.name.lower()}]({thread.jump_url}) |" if thread else ""
        )
    properties.update(footer=footer, description=description)
    return properties


class MainMessageHandler(HandlerABC):
    def __init__(self):
        self.__message: Optional[discord.Message] = None

    @property
    def message(self):
        return self.__message

    @property
    def looping(self):
        return MainView.from_message(self.message).looping

    @property
    def shuffle(self):
        return MainView.from_message(self.message).shuffle

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

    def update_main_view(self):
        self.client.add_view(MainView(), message_id=self.message.id)

    @staticmethod
    def create_file(
        path: str = "Music_cog/room/other_files/banner.gif",
        name: str = "Banner.gif",
    ) -> discord.File:
        return discord.File(open(path, "rb"), filename=name)

    @staticmethod
    def create_embed(guild: discord.Guild, settings: dict = None) -> discord.Embed:
        if settings is None:
            settings = {
                "title": "Queue is clear",
                "type": "rich",
                "color": 0x00FF00,
                "image": {"url": conf["back_image"]},
            }
        default_properties = create_default_embed_properties(guild)
        settings.update(default_properties)

        embed = discord.Embed.from_dict(settings)
        return embed

    async def update_embed(self, guild: discord.Guild, track: Track = None):
        settings = None
        if track is not None:
            settings = {
                "title": track.title,
                "type": "rich",
                "color": 0x00FF00,
                "timestamp": str(track.requested_at),
                "url": track.track_url,
                "author": {"name": track.artist, "url": track.artist_url},
                "image": {"url": track.thumbnail},
                "fields": [
                    {
                        "name": "Request Info",
                        "inline": True,
                        "value": f"Requested by {track.requested_by.mention}{rofl(track.requested_by)}\n\
                                Requested <t:{track.requested_at.timestamp().__ceil__()}:R>"
                    },
                ],
            }
        new_embed = self.create_embed(guild, settings)
        await self.message.edit(embed=new_embed)


class SettingsThreadHandler(ThreadHandlerABC):
    @property
    async def search_platform(self) -> SearchPlatform:
        thread_message: discord.Message = await self.get_thread_message(self.thread)  # type: ignore
        return SettingsView.from_message(thread_message).search_platform  # type: ignore

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
