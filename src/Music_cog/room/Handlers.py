import re
from typing import Self

import discord
from loguru import logger

from ABC import HandlerABC, ThreadHandlerABC
from Bot import TenB_Bot
from enums import SearchPlatform, Shuffle, ThreadType
from Music_cog import Utils
from Music_cog.player.Track import Track

from .Embeds import (
    EmbedDefault,
    EmbedPlayingTrack,
    EmbedTrack,
    set_discription_from_track,
)
from .Views import PlayerView, SettingsView, setup_view_client


def setup(client: TenB_Bot):
    setup_view_client(client)
    HandlerABC._client = client


class MessageHandler(HandlerABC):
    def __init__(self, message: discord.Message):
        self.__message: discord.Message = message

    @property
    def message(self):
        return self.__message


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
    async def from_room(cls, room: discord.TextChannel | None) -> Self | None:
        if room:
            message = await cls.get_main_message(room)
        return cls(message) if room and message else None

    @staticmethod
    async def get_main_message(room: discord.TextChannel) -> discord.Message | None:
        try:
            async for message in room.history():
                if len(message.embeds) > 0 and message.author == PlayerMessageHandler._client.user:
                    return message
        except Exception as e:
            logger.error(f"NO MAIN MESSAGE - {e}")
        return None

    async def update_main_view(self):
        view = PlayerView.from_message(self.message)
        view.set_to_default_view()
        await self.message.edit(view=view)
        self.client.add_view(PlayerView(), message_id=self.message.id)

    async def update_playing_track_embed(
        self, guild: discord.Guild, track: Track | None = None, shuffle: Shuffle = Shuffle.NOSHUFFLE
    ):
        await self.message.edit(embed=EmbedPlayingTrack(guild, track, shuffle) if track else EmbedDefault(guild, shuffle))


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

        await self.thread.send(embed=EmbedTrack(track, track_number))

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
        async for message in self.thread.history():
            if len(message.embeds) > 0:
                embed = message.embeds[0]
                if embed.author.name == track.author and embed.title == track.title and isinstance(embed.description, str):
                    for search_plat in SearchPlatform:
                        if re.search(search_plat.value, embed.description):
                            match = re.search(r"\d+", message.clean_content)
                            content = f"{int(match.group()) + 1} times" if match else "2 times"
                            await message.edit(content=content, embed=set_discription_from_track(embed, track))
                            return
                break
        await self.thread.send(embed=EmbedTrack(track))


async def update_threads_views(guild: discord.Guild):
    for thread_type in ThreadType:
        match thread_type:
            case ThreadType.SETTINGS:
                if thread := Utils.get_thread(guild, thread_type):
                    await SettingsThreadHandler(thread).update_thread_views()
