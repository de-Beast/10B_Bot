import re
from typing import Self

import discord
from loguru import logger

from ABC import HandlerABC, ThreadHandlerABC
from Bot import TenB_Bot
from enums import SearchPlatform, ThreadType
from Music_cog import Utils
from Music_cog.player.Track import Track

from .Embeds import EmbedDefault, EmbedPlayer, EmbedTrack, update_discription_from_track
from .Views import PlayerView, SettingsView, setup_view_client


def setup(client: TenB_Bot):
    setup_view_client(client)
    HandlerABC._client = client


class MessageHandler(HandlerABC):
    def __init__(self, message: discord.Message):
        self.__message: discord.Message = message
        self.__guild: discord.Guild = message.guild  # type: ignore

    @property
    def message(self):
        return self.__message

    @property
    def guild(self):
        return self.__guild


class PlayerMessageHandler(MessageHandler):
    @property
    def loop(self):
        return PlayerView.from_message(self.message).loop

    @property
    def shuffle(self):
        return PlayerView.from_message(self.message).shuffle

    @property
    def channel(self):
        return self.message.channel

    @classmethod
    async def from_guild_async(cls, guild: discord.Guild | None) -> Self | None:
        if room := Utils.get_music_room(guild):
            message = await cls.get_main_message(room)
        return cls(message) if room and message else None

    @classmethod
    async def from_room(cls, room: discord.TextChannel | None) -> Self | None:
        if room:
            message = await cls.get_main_message(room)
        return cls(message) if room and message else None

    @staticmethod
    async def get_main_message(room: discord.TextChannel) -> discord.Message | None:
        try:
            async for message in room.history():
                if (
                    len(message.embeds) > 0
                    and message.author == PlayerMessageHandler._client.user
                ):
                    return message
        except Exception as e:
            logger.error(f"NO MAIN MESSAGE - {e}")
        return None

    async def reset_main_view(self):
        view = PlayerView.from_message(self.message)
        view.set_to_default_view()
        await self.message.edit(view=view)
        self.client.add_view(PlayerView(), message_id=self.message.id)

    async def update_playing_track_embed(
        self,
        track: Track | None = None,
    ):
        await self.message.edit(
            embed=await EmbedPlayer.create_with_updated_footer(self.guild, track)
            if track
            else await EmbedDefault.create_with_updated_footer(self.guild)
        )


class SettingsThreadHandler(ThreadHandlerABC):
    @classmethod
    def from_guild(cls, guild: discord.Guild) -> Self | None:
        thread = Utils.get_thread(guild, ThreadType.SETTINGS)
        return cls(thread) if thread else None
    
    @staticmethod
    def check(thread: "ThreadHandlerABC") -> bool:
        return thread.thread == Utils.get_thread(thread.thread.guild, ThreadType.SETTINGS)

    async def get_search_platform(self) -> SearchPlatform:
        thread_message: discord.Message | None = await self.get_thread_message(
            self.thread
        )
        return (
            SettingsView.from_message(thread_message).search_platform
            if thread_message is not None
            else SearchPlatform.YOUTUBE
        )

    @staticmethod
    async def get_thread_message(thread: discord.Thread) -> discord.Message | None:
        try:
            async for message in thread.history(limit=1, oldest_first=True):
                return message
        except Exception as e:
            logger.warning("NO THREAD MESSAGE FOR U @", e)
        return None

    async def update_thread_views(self):
        if thread_message := await self.get_thread_message(self.thread):
            self.client.add_view(
                SettingsView(),
                message_id=thread_message.id,
            )


class QueueThreadHandler(ThreadHandlerABC):
    def __init__(self, thread: discord.Thread):
        super().__init__(thread)
        self._track_messages: dict[int, int] = {}

    @classmethod
    def from_guild(cls, guild: discord.Guild) -> Self | None:
        thread = Utils.get_thread(guild, ThreadType.QUEUE)
        return cls(thread) if thread else None

    @staticmethod
    def check(thread: "ThreadHandlerABC") -> bool:
        return thread.thread == Utils.get_thread(thread.thread.guild, ThreadType.QUEUE)

    async def send_track_message(
        self, track: Track, track_index: int, *, is_playing: bool = False
    ) -> None:
        embed = EmbedTrack(track, track_index + 1)
        if is_playing:
            embed = EmbedTrack.update_color(embed)
        message = await self.thread.send(embed=embed)
        self._track_messages[track_index] = message.id

    async def update_track_color(
        self, track_number: int, *, is_playing: bool = True
    ) -> None:
        if message_id := self._track_messages.get(track_number):
            message = await self.thread.fetch_message(message_id)
            embed = message.embeds[0]
            embed = EmbedTrack.update_color(embed, is_playing=is_playing)
            await message.edit(embed=embed)

    async def remove_track_message(self, /, *, all: bool = False) -> None:
        await self.thread.purge(
            limit=1 if not all else None,
            check=lambda m: m.author == self.client.user,
            oldest_first=True,
        )
        if not all:
            await self.update_track_numbers()
        else:
            self._track_messages = {}

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
    @classmethod
    def from_guild(cls, guild: discord.Guild) -> Self | None:
        thread = Utils.get_thread(guild, ThreadType.HISTORY)
        return cls(thread) if thread else None

    @staticmethod
    def check(thread: "ThreadHandlerABC") -> bool:
        return thread.thread == Utils.get_thread(thread.thread.guild, ThreadType.HISTORY)

    async def store_track_in_history(self, track: Track) -> None:
        async for message in self.thread.history():
            if len(message.embeds) > 0:
                embed = message.embeds[0]
                if (
                    embed.author.name == track.author
                    and embed.title == track.title
                    and isinstance(embed.description, str)
                ):
                    for search_plat in SearchPlatform:
                        if re.search(search_plat.value, embed.description):
                            match = re.search(r"\d+", message.clean_content)
                            content = (
                                f"{int(match.group()) + 1} times"
                                if match
                                else "2 times"
                            )
                            await message.edit(
                                content=content,
                                embed=update_discription_from_track(embed, track),
                            )
                            return
                break
        await self.thread.send(embed=EmbedTrack(track))


async def update_threads_views(guild: discord.Guild):
    for thread_type in ThreadType:
        match thread_type:
            case ThreadType.SETTINGS:
                if handler := SettingsThreadHandler.from_guild(guild):
                    await handler.update_thread_views()
