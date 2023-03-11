import asyncio
from threading import Condition, Thread

import discord
from discord.ext import bridge, tasks
from loguru import logger

from enums import Loop, SearchPlatform, Shuffle
from Music_cog import Utils
from Music_cog.room.Handlers import PlayerMessageHandler

from . import Player_utils as plUtils
from .Queue import Queue
from .Track import MetaData, Track, TrackInfo

TIMEOUT = 20


def _notify_and_close_condition(cond: Condition):
    with cond:
        cond.notify_all()


class MusicPlayer(discord.VoiceClient):
    # TODO: Сделать работу с плейлистами (вроде изи)
    def __init__(self, client: bridge.Bot, channel: discord.VoiceChannel):
        super().__init__(client, channel)
        self.disconnect_timeout.start()
        self._queue: Queue = Queue(channel.guild)
        self._playing_track = None

        self._inited = False

    async def init(self) -> None:
        await self._queue.init()
    
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

    @shuffle.setter
    def shuffle(self, shuffle_type: Shuffle):
        self._queue.shuffle = shuffle_type

    async def play_next(self, loop: asyncio.AbstractEventLoop):
        cond = Condition()

        async def _wait_for_end(cond: Condition, loop: asyncio.AbstractEventLoop) -> None:
            with cond:
                cond.wait()
                await self._queue.update_queue(loop)

        if self._playing_track is None:
            return

        self.play(self._playing_track.src, after=lambda x: _notify_and_close_condition(cond))
        self._queue.new_track = False
        Thread(target=asyncio.run, args=(_wait_for_end(cond, loop),)).start()

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

    async def add_query(self, query: str, search_platform: SearchPlatform, request_data: MetaData) -> None:
        coro = asyncio.create_task(plUtils.define_stream_method(query, search_platform, request_data))
        await asyncio.wait_for(coro, timeout=20)
        tracks_all_meta = coro.result()
        await self._add_tracks_to_queue(tracks_all_meta)

    async def _add_tracks_to_queue(self, tracks_all_meta: list[TrackInfo | None]) -> None:
        if len(tracks_all_meta) == 1 and None in tracks_all_meta:
            logger.error("No tracks to add to queue")
            if handler := await self._player_message_handler:
                await handler.channel.send("No tracks were found", delete_after=5)
            return
        for track_all_meta in tracks_all_meta:
            if not track_all_meta:
                continue

            track = await Track.from_dict(track_all_meta)
            await self._queue.add_track(track)

            logmessage = "TRACKS QUEUE:"
            for track in self._queue:
                logmessage += "\n" + str(track)
            logger.opt(colors=True).info(logmessage)
            if not self.has_track:
                self.play_music.start()

    async def disconnect(self, *, force: bool = False):
        await self.stop_player()
        self.disconnect_timeout.cancel()
        await super().disconnect(force=force)
        await self.voice_disconnect()

    @tasks.loop(seconds=1)
    async def play_music(self):
        if self._queue.current_track is None:
            self._playing_track = None
            if handler := await self._player_message_handler:
                await handler.update_playing_track_embed(self.guild, self.track, self.shuffle)
            self.play_music.cancel()
        elif self._queue.new_track:
            self._playing_track = await self.track.copy()
            if handler := await self._player_message_handler:
                await handler.update_playing_track_embed(self.guild, self.track, self.shuffle)
            await self.play_next(self.play_music.loop)

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
