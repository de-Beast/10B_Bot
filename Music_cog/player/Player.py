import asyncio
from threading import Condition, Thread

import discord
from discord.ext import bridge, tasks
from loguru import logger

from enums import Loop, SearchPlatform, Shuffle

from . import Player_utils as plUtils
from .Queue import Queue
from .Track import Track, TrackInfo

TIMEOUT = 60


def _notify_and_close_condition(cond: Condition):
    with cond:
        cond.notify_all()


class MusicPlayer(discord.VoiceClient):
    # TODO: Сделать работу с плейлистами (вроде изи)
    def __init__(self, client: bridge.Bot, channel: discord.VoiceChannel):
        super().__init__(client, channel)
        self.disconnect_timeout.start()
        self.__queue: Queue = Queue(channel.guild)
        self._playing_track = None

    @property
    def has_track(self) -> bool:
        return self.is_playing() or self.is_paused()

    @property
    def track(self) -> Track | None:
        return self.__queue.current_track

    @property
    def looping(self) -> Loop:
        return self.__queue.looping

    @looping.setter
    def looping(self, loop_type: Loop):
        self.__queue.looping = loop_type

    @property
    def shuffle(self) -> Shuffle:
        return self.__queue.shuffle

    @shuffle.setter
    def shuffle(self, shuffle_type: Shuffle):
        self.__queue.shuffle = shuffle_type

    @tasks.loop(seconds=1)
    async def play_music(self):
        if self.__queue.current_track is None:
            self._playing_track = None
            self.play_music.cancel()
        elif self.__queue.new_track:
            self._playing_track = await self.track.copy()
            await self.play_next(self.play_music.loop)

    async def play_next(self, loop: asyncio.AbstractEventLoop):
        cond = Condition()

        async def _wait_for_end(
            cond: Condition, loop: asyncio.AbstractEventLoop
        ) -> None:
            with cond:
                cond.wait()
                await self.__queue.update_queue(loop)

        self.play(
            self._playing_track.src, after=lambda x: _notify_and_close_condition(cond)  # type: ignore
        )
        self.__queue.new_track = False
        self.pause()
        await asyncio.sleep(1)
        self.resume()
        Thread(target=asyncio.run, args=(_wait_for_end(cond, loop),)).start()

    async def stop_player(self):
        if self.has_track:
            await self.__queue.clear()
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
            self.__queue.prepare_prev_track()
            self.stop()

    async def add_query(
        self, query: str, search_platform: SearchPlatform, message: discord.Message
    ) -> None:
        coro = asyncio.create_task(
            plUtils.define_stream_method(query, search_platform, message)
        )
        await asyncio.wait_for(coro, timeout=20)
        tracks_all_meta = coro.result()
        await self._add_tracks_to_queue(tracks_all_meta)

    async def _add_tracks_to_queue(
        self, tracks_all_meta: list[TrackInfo | None]
    ) -> None:
        if tracks_all_meta is None:
            logger.error("No tracks to add to queue")
            return
        for track_all_meta in tracks_all_meta:
            if not track_all_meta:
                continue

            track = await Track.from_dict(track_all_meta)
            await self.__queue.add_track(track)

            logmessage = "TRACKS QUEUE:"
            for track in self.__queue:
                logmessage += "\n" + str(track)
            logger.opt(colors=True).info(logmessage)
            if not self.has_track:
                self.play_music.start()

    async def disconnect(self, *, force: bool = False):
        await super().disconnect(force=force)
        await self.stop_player()
        self.disconnect_timeout.cancel()

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
