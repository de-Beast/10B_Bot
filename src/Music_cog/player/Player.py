import asyncio
from typing import Coroutine, Generator

import discord
import discord.types
import discord.types.voice
from discord.ext import bridge, tasks
from loguru import logger

from enums import Loop, Shuffle
from Music_cog.room.Handlers import PlayerMessageHandler

from .DownloadMethodResolver import DownloadMethodResolver
from .Queue import Queue
from .Track import MetaData, Track, TrackInfo

TIMEOUT = 60


class MusicPlayer(discord.VoiceClient):
    def __init__(self, client: bridge.Bot, channel: discord.VoiceChannel):
        super().__init__(client, channel)
        self._guild = channel.guild

        self.disconnect_timeout.start()

        self._queue: Queue = Queue(client, channel.guild)
        self._is_queue_inited = False

        self._add_tracks_coros: list[Coroutine] = []
        self._add_tracks_task: asyncio.Task | None = None
        self._play_task: asyncio.Task | None = None

        self._track: Track | None = None

    @property
    def guild(self) -> discord.Guild:
        return self._guild

    @property
    async def _player_message_handler(self) -> PlayerMessageHandler | None:
        return await PlayerMessageHandler.from_guild_async(self.guild)

    @property
    def is_playing_or_paused(self) -> bool:
        return self.is_playing() or self.is_paused()

    @property
    def track(self) -> Track | None:
        return self._track

    def prepare_next_track(self, *, force=False) -> None:
        if self.queue.state is Queue.State.START:
            self._track = self.queue.current()
            return
        if (
            self.queue.looping is Loop.NOLOOP
            and self.queue.state is Queue.State.RUNNING
        ):
            self._track = self.queue.next()
            return
        self._track = self.queue.next(force=force)

    def prepare_prev_track(self, *, repeat_current: bool = False) -> None:
        if repeat_current or self.queue.state is Queue.State.END:
            if not self._track:
                self._track = self.queue.current()
            return

        self._track = self.queue.prev()

    @property
    def looping(self) -> Loop:
        return self.queue.looping

    @looping.setter
    def looping(self, looping: Loop):
        self.queue.looping = looping

    @property
    def shuffle(self) -> Shuffle:
        return self.queue.shuffle

    @property
    def queue(self) -> Queue:
        return self._queue

    async def set_shuffle(self, shuffle_type: Shuffle):
        await self.queue.set_shuffle(shuffle_type)

    async def stop_player(self):
        self._add_tracks_coros.clear()
        if self._add_tracks_task:
            self._add_tracks_task.cancel()
            await self._add_tracks_task
            self._add_tracks_task = None

        await self.queue.clear()
        if self.is_playing_or_paused:
            self.stop()
        self._track = None
        await self.before_play()

    def toggle(self):
        if self.is_playing():
            self.pause()
        elif self.is_paused():
            self.resume()

    async def set_audio_source(self):
        if not await self.before_play():
            self.stop()
            return

        track = await self.track.copy()  # type: ignore
        self.source = track.src

    def skip(self):
        if len(self.queue) == 0:
            return

        self.prepare_next_track(force=True)
        if not self.is_playing_or_paused:
            self._play_task = self.loop.create_task(self.play_next())
        else:
            self.loop.create_task(self.set_audio_source())

    def prev(self):
        if len(self.queue) == 0:
            return

        self.prepare_prev_track()
        if not self.is_playing_or_paused:
            self._play_task = self.loop.create_task(self.play_next())
        else:
            self.loop.create_task(self.set_audio_source())

    def repeat_current(self):
        if len(self.queue) == 0:
            return

        self.prepare_prev_track(repeat_current=True)
        if not self.is_playing_or_paused:
            self._play_task = self.loop.create_task(self.play_next())
        else:
            self.loop.create_task(self.set_audio_source())

    async def before_play(self) -> bool:
        if handler := await self._player_message_handler:
            await handler.update_playing_track_embed(self.track)

        return self.track is not None

    async def play_next(self):
        if not await self.before_play():
            self._play_task = None
            return

        if not self.is_playing_or_paused:
            track: Track = await self.track.copy()  # type: ignore
            self.play(track.src, after=self.after_play)

    def after_play(self, error: Exception | None = None):
        if error:
            logger.error(error)
        self.prepare_next_track()
        self._play_task = self.loop.create_task(self.play_next())

    async def add_query(self, query: str, request_data: MetaData) -> None:
        resolver = DownloadMethodResolver(query, request_data)
        tracks_info = await resolver.proccess_query()
        if self._add_tracks_task is None:
            self._add_tracks_task = asyncio.create_task(
                self._add_tracks_to_queue(tracks_info)
            )
            self._add_tracks_task.add_done_callback(self._after_add_tracks_to_queue)
        else:
            self._add_tracks_coros.append(self._add_tracks_to_queue(tracks_info))

    def _after_add_tracks_to_queue(
        self,
        task: asyncio.Task[Generator[TrackInfo, None, None] | TrackInfo | None],
    ) -> None:
        if len(self._add_tracks_coros) > 0:
            self._add_tracks_task = asyncio.create_task(self._add_tracks_coros.pop(0))
            self._add_tracks_task.add_done_callback(self._after_add_tracks_to_queue)
        else:
            self._add_tracks_task = None

    async def _add_tracks_to_queue(
        self, tracks_info: Generator[TrackInfo, None, None] | TrackInfo | None
    ) -> None:
        if not self.is_connected():
            logger.error("Voice protocol is not removed from the internal state cache")
            if handler := await self._player_message_handler:
                await handler.channel.send(
                    "Please, wait a moment, we need to clean up 🧹", delete_after=10
                )
            return

        if tracks_info is None:
            logger.error("No tracks to add to queue")
            if handler := await self._player_message_handler:
                await handler.channel.send("No tracks were found", delete_after=5)
            return

        if not self._is_queue_inited:
            self._is_queue_inited = True
            await self.queue.init()

        try:
            if isinstance(tracks_info, dict):
                track = await Track.from_dict(tracks_info)
                await self.queue.add_track(track)
            else:
                for track_info in tracks_info:
                    track = await Track.from_dict(track_info)
                    await self.queue.add_track(track)
        except asyncio.CancelledError:
            logger.error("Add tracks task is Cancelled")
        else:
            if not self._play_task:
                self.prepare_next_track()
                self._play_task = self.loop.create_task(self.play_next())

            logmessage = "TRACKS QUEUE:"
            for track in self.queue:
                logmessage += "\n" + str(track)
            logger.opt(colors=True).info(logmessage)

    async def disconnect(self, *, force: bool = False):
        self.disconnect_timeout.stop()
        await self.stop_player()
        await super().disconnect(force=force)

    @tasks.loop(seconds=5)
    async def disconnect_timeout(self):
        c = 0
        while not self.is_playing_or_paused:
            await asyncio.sleep(1)
            c += 1
            if self.is_playing_or_paused:
                break
            elif c == TIMEOUT:
                await self.disconnect(force=True)
