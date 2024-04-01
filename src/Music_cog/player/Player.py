import asyncio
import itertools
from pickle import FALSE
from typing import Any, Coroutine, Generator, Literal, overload

import discord
from discord.ext import bridge, tasks
from loguru import logger

from enums import Loop, Shuffle
from Music_cog import Utils
from Music_cog.room.Handlers import PlayerMessageHandler

from . import DownloadMethodResolver as plUtils
from .Queue import Queue
from .Track import MetaData, Track, TrackInfo

TIMEOUT = 60


class _MissingSentinel:
    def __eq__(self, other) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "..."


MISSING: Any = _MissingSentinel()

# TODO: Исправить зависимости от многих состояний (self.track, self.has_track, self._playing_track и т.д.)


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

        self._track: Track | None = MISSING

    @property
    def guild(self) -> discord.Guild:
        return self._guild

    @property
    async def _player_message_handler(self) -> PlayerMessageHandler | None:
        return await PlayerMessageHandler.from_room(Utils.get_music_room(self.guild))

    @property
    def has_track(self) -> bool:
        return self.is_playing() or self.is_paused()

    @property
    def track(self) -> Track | None:
        if self._track is MISSING:
            return None
        return self._track

    def prepare_next_track(self, *, force=False) -> None:
        if not self.queue.is_started:
            self._track = self.queue.current()
            return

        self._track = self.queue.next(force=force)

    def prepare_prev_track(self) -> None:
        if not self.has_track and len(self.queue) > 0:
            self._track = self.queue.current()
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

        await self.queue.clear()
        if self.has_track:
            self.stop()
        self._track = MISSING

    def toggle(self):
        if self.is_playing():
            self.pause()
        elif self.is_paused():
            self.resume()

    async def set_audio_source(self):
        if not await self.before_play():
            return

        track = await self.track.copy()  # type: ignore
        self.source = track.src

    def skip(self):
        if len(self.queue) == 0:
            return

        match self.looping:
            case Loop.NOLOOP:
                self.prepare_next_track(force=self.has_track)
            case _:
                self.prepare_next_track(force=True)
        self.loop.create_task(self.set_audio_source())

    def prev(self):
        if len(self.queue) == 0:
            return

        self.prepare_prev_track()
        self.loop.create_task(self.set_audio_source())

    async def before_play(self) -> bool:
        if handler := await self._player_message_handler:
            await handler.update_playing_track_embed(self.guild, self.track)

        return self.track is not None

    async def play_next(self):
        if not await self.before_play():
            self._play_task = None
            return

        track: Track = await self.track.copy()  # type: ignore
        self.play(track.src, after=self.after_play)

    def after_play(self, error: Exception | None = None):
        if error:
            logger.error(error)
        self.prepare_next_track()
        self._play_task = self.loop.create_task(self.play_next())

    async def add_query(self, query: str, request_data: MetaData) -> None:
        resolver = plUtils.DownloadMethodResolver(query, request_data)
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
            if not self.has_track:
                self.after_play()

            logmessage = "TRACKS QUEUE:"
            for track in self.queue:
                logmessage += "\n" + str(track)
            logger.opt(colors=True).info(logmessage)

    async def disconnect(self, *, force: bool = False):
        await self.stop_player()
        self.disconnect_timeout.cancel()
        await super().disconnect(force=force)
        await self.voice_disconnect()

    @tasks.loop(seconds=5)
    async def disconnect_timeout(self):
        c = 0
        while not self.has_track:
            await asyncio.sleep(1)
            c += 1
            if self.has_track:
                break
            elif c == TIMEOUT:
                await self.disconnect(force=True)
