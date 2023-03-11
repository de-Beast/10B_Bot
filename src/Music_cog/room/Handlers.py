import random
from typing import TYPE_CHECKING, Any, Self

import discord
from loguru import logger

from ABC import HandlerABC, ThreadHandlerABC
from Bot import TenB_Bot
from enums import SearchPlatform, Shuffle, ThreadType
from Music_cog import Utils
from Music_cog.player.Track import Track

from .message_config import message_config
from .Views import MainView, SettingsView, setup_view_client

if TYPE_CHECKING:
    pass


def rofl(requester: discord.User | discord.Member) -> str:
    rofl_str = " – "
    match requester.id:
        case 447849746586140672:
            rofl_str += random.choice(("ПОПУЩЕНЕЦ", "ОБСОСИК", "БЕРСЕРК ГАВНИЩЕ ЕБУЧЕЕ"))
        case 446753575465385998:
            rofl_str += random.choice(
                (
                    "ВОТ БЫ ТЫ НЕ РАЗГОВАРИВАЛ",
                    "ЖИРНОЕ ЧМО",
                    "КАКАЯ ЖЕ НАСТЕНЬКА ОХУИТЕЛЬНАЯ",
                )
            )
        case 309011989286354944:
            rofl_str += random.choice(("МОЯ СЛАДЕНЬКАЯ БУЛОЧКА", "АНИМЕШНИК", "ТРАХНИ МЕНЯ"))
        case 600361186495692801:
            rofl_str += random.choice(("ЛУЧШИЙ В МИРЕ", "СПАСИБО ЗА БОТА", "АПНУЛ ВТОРУЮ ПЛАТИНУ"))
    return rofl_str if len(rofl_str) > 3 else ""


def setup(client: TenB_Bot):
    setup_view_client(client)
    HandlerABC._client = client


def create_default_embed_properties(guild: discord.Guild | None = None) -> dict:
    properties: dict[str, Any] = {"type": "rich", "color": 0x00FF00}
    if guild is not None:
        description = "|"
        for thread_type in ThreadType:
            thread = Utils.get_thread(guild, thread_type)
            description += f" [{thread_type.name.lower()}]({thread.jump_url}) |" if thread else ""
        properties.update(description=description)
    return properties


class MessageHandler(HandlerABC):
    def __init__(self, message: discord.Message):
        self.__message: discord.Message = message

    @property
    def message(self):
        return self.__message

    @staticmethod
    def create_embed_from_track(track: Track, number: int | None = None) -> discord.Embed:
        settings = {
            "title": track.title,
            "timestamp": str(track.requested_at),
            "url": track.track_url,
            "author": {"name": f"{number}. {track.artist}" if number else f"{track.artist}", "url": track.artist_url},
            "description": f"Requested by {track.requested_by.mention}{rofl(track.requested_by)}\n\
                            <t:{track.requested_at.timestamp().__ceil__()}:R>",
        }
        default_properties = create_default_embed_properties()
        settings.update(default_properties)

        embed = discord.Embed.from_dict(settings)
        return embed

    async def update_embed_with_embed(self, embed: discord.Embed) -> discord.Embed:
        next_embed = self.__message.embeds[0]
        await self.message.edit(embed=embed)
        return next_embed


class PlayerMessageHandler(MessageHandler):
    @property
    def looping(self):
        return MainView.from_message(self.message).looping

    @property
    def shuffle(self):
        return MainView.from_message(self.message).shuffle

    @property
    def channel(self):
        return self.message.channel

    @classmethod
    async def with_message_from_room(cls, room: discord.TextChannel | None) -> Self | None:
        if room:
            message = await cls.get_main_message(room)
        return cls(message) if room and message else None

    @staticmethod
    async def get_main_message(room: discord.TextChannel) -> discord.Message | None:
        try:
            async for message in room.history(oldest_first=True):
                if len(message.embeds) > 0:
                    return message
        except Exception as e:
            logger.error(f"NO MAIN MESSAGE - {e}")
        return None

    @staticmethod
    def create_main_view() -> MainView:
        return MainView()

    async def update_main_view(self):
        backed_view = MainView.from_message(self.message)
        backed_view.set_to_default_view()
        await self.message.edit(view=backed_view)
        self.client.add_view(MainView(), message_id=self.message.id)

    @staticmethod
    def create_embed(
        guild: discord.Guild,
        settings: dict | None = None,
        shuffle: Shuffle | None = None,
    ) -> discord.Embed:
        if shuffle is None:
            shuffle = Shuffle.NOSHUFFLE
        match shuffle:
            case Shuffle.NOSHUFFLE:
                footer = "Using default queue"
            case Shuffle.SHUFFLE:
                footer = "Using shuffled queue"
            case Shuffle.SECRET:
                footer = "Using secretly shuffled queue"
        if settings is None:
            settings = {
                "title": "Queue is clear",
                "image": {"url": message_config["back_image"]},
            }
        default_properties = create_default_embed_properties(guild)
        settings.update(default_properties, footer={"text": footer})

        embed = discord.Embed.from_dict(settings)
        return embed

    async def update_embed(
        self,
        guild: discord.Guild,
        track: Track | None = None,
        shuffle: Shuffle | None = None,
    ):
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
                                <t:{track.requested_at.timestamp().__ceil__()}:R>",
                    },
                ],
            }
        new_embed = self.create_embed(guild, settings, shuffle)
        await self.message.edit(embed=new_embed)


class SettingsThreadHandler(ThreadHandlerABC):
    @property
    async def search_platform(self) -> SearchPlatform:
        thread_message: discord.Message | None = await self.get_thread_message(self.thread)
        return (
            SettingsView.from_message(thread_message).search_platform if thread_message is not None else SearchPlatform.YOUTUBE
        )

    @staticmethod
    async def get_thread_message(thread: discord.Thread) -> discord.Message | None:
        try:
            async for message in thread.history(limit=1, oldest_first=True):
                return message
        except Exception as e:
            logger.warning("NO THREAD MESSAGE FOR U @", e)
        return None

    @staticmethod
    def create_settings_view() -> SettingsView:
        return SettingsView()

    async def update_thread_views(self):
        thread_message = await self.get_thread_message(self.thread)
        self.client.add_view(
            SettingsView(),
            message_id=thread_message.id,
        )


class QueueThreadHandler(ThreadHandlerABC):
    async def send_track_message(self, track: Track, track_number: int, /, *, is_loop: bool = False) -> None:
        if is_loop:
            await self.thread.purge(limit=1, check=lambda m: m.author == self.client.user, oldest_first=True)
            await self.update_track_numbers()

        embed = MessageHandler.create_embed_from_track(track, track_number)
        await self.thread.send(embed=embed)

    async def remove_track_message(self, /, *, all: bool = False) -> None:
        await self.thread.purge(
            limit=1 if not all else None,
            check=lambda m: m.author == self.client.user,
            oldest_first=True,
        )
        if not all:
            await self.update_track_numbers()

    async def update_track_numbers(self) -> None:
        counter = 1
        async for message in self.thread.history(oldest_first=True):
            if message.author == self.client.user:
                embed = message.embeds[0]
                embed.set_author(
                    name=f"{counter}. {embed.author.name.split()[1]}",
                    url=embed.author.url,
                    icon_url=embed.author.icon_url,
                )
                await message.edit(embed=embed)
                counter += 1


class HistoryThreadHandler(ThreadHandlerABC):
    async def store_track_in_history(self, track: Track) -> None:
        embed = MessageHandler.create_embed_from_track(track)
        await self.thread.send(embed=embed)


async def update_threads_views(guild: discord.Guild):
    for thread_type in ThreadType:
        match thread_type:
            case ThreadType.SETTINGS:
                if thread := Utils.get_thread(guild, thread_type):
                    await SettingsThreadHandler(thread).update_thread_views()
