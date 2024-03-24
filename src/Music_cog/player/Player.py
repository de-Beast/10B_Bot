import asyncio
from typing import Generator

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

# TODO: Исправить зависимости от многих состояний (self.track, self.has_track, self._playing_track и т.д.)


class MusicPlayer(discord.VoiceClient):
    def __init__(self, client: bridge.Bot, channel: discord.VoiceChannel):
        super().__init__(client, channel)
        self._guild = channel.guild

        self.disconnect_timeout.start()

        self._queue: Queue = Queue(channel.guild)
        self._playing_track = None

        self._is_queue_inited = False

        self._query_tasks: list[asyncio.Task] = []

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
        return self._queue.current_track

    @property
    def looping(self) -> Loop:
        return self._queue.loop

    @looping.setter
    def looping(self, loop_type: Loop):
        self._queue.loop = loop_type

    @property
    def shuffle(self) -> Shuffle:
        return self._queue.shuffle

    async def set_shuffle(self, shuffle_type: Shuffle):
        await self._queue.set_shuffle(shuffle_type)

    async def play_next(self):
        if self._playing_track is None:
            return

        self.play(self._playing_track.src, after=self.after_play)
        self._queue.new_track = False

    def after_play(self, error: Exception | None = None):
        if error:
            logger.error(error)
        self._queue.update_queue()

    async def stop_player(self):
        if self.has_track:
            await self._queue.clear()
            self.stop()

    def toggle(self):
        if self.is_playing():
            self.pause()
        elif self.is_paused():
            self.resume()

    def skip(self):
        if self.has_track:
            self.stop()

    def prev(self):
        if self.has_track:
            self._queue.prepare_prev_track()
            self.stop()

    async def add_query(self, query: str, request_data: MetaData) -> None:
        resolver = plUtils.DownloadMethodResolver(query, request_data)
        task = asyncio.create_task(resolver.proccess_query())
        task.add_done_callback(self._proccess_query_callback)

    def _proccess_query_callback(
        self,
        future: asyncio.Task[Generator[TrackInfo, None, None] | TrackInfo | None],
    ) -> None:
        tracks_all_meta = future.result()
        task = asyncio.create_task(self._add_tracks_to_queue(tracks_all_meta))
        task.add_done_callback(self._remove_task_from_list)
        self._query_tasks.append(task)

    def _remove_task_from_list(self, task: asyncio.Task) -> None:
        self._query_tasks.remove(task)

    async def _try_start_audio_cycle(self):
        if not self.has_track and not self.play_music.is_running():
            self.play_music.start()
            if not self._is_queue_inited:
                self._is_queue_inited = True
                await self._queue.init(self.play_music.loop)

    async def _add_tracks_to_queue(
        self, tracks_info: Generator[TrackInfo, None, None] | TrackInfo | None
    ) -> None:
        if tracks_info is None:
            logger.error("No tracks to add to queue")
            if handler := await self._player_message_handler:
                await handler.channel.send("No tracks were found", delete_after=5)
            return

        if isinstance(tracks_info, dict):
            track = await Track.from_dict(tracks_info)
            await self._queue.add_track(track)
            await self._try_start_audio_cycle()
        else:
            for track_info in tracks_info:
                track = await Track.from_dict(track_info)
                await self._queue.add_track(track)
                await self._try_start_audio_cycle()

        logmessage = f"TRACKS QUEUE:\n{self.track}"
        for track in self._queue:
            logmessage += "\n" + str(track)
        logger.opt(colors=True).info(logmessage)

    async def disconnect(self, *, force: bool = False):
        await self.stop_player()
        for task in self._query_tasks.copy():
            task.cancel()
        self.disconnect_timeout.cancel()
        await super().disconnect(force=force)
        await self.voice_disconnect()

    @tasks.loop(seconds=1)
    async def play_music(self):
        if self._queue.current_track is None:
            self._playing_track = None
            if handler := await self._player_message_handler:
                await handler.update_playing_track_embed(
                    self.guild, self.track, self.shuffle
                )
            self.play_music.cancel()
        elif self._queue.new_track:
            self._playing_track = await self.track.copy() if self.track else None
            if handler := await self._player_message_handler:
                await handler.update_playing_track_embed(
                    self.guild, self.track, self.shuffle
                )
            await self.play_next()

    @tasks.loop(seconds=5)
    async def disconnect_timeout(self):
        c = 0
        while not self.has_track:
            await asyncio.sleep(1)
            c += 1
            if self.has_track:
                break
            elif c == TIMEOUT:
                await self.disconnect()
