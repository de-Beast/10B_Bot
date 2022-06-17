import asyncio
from threading import Condition, Thread
from typing import Optional

import discord
from discord.ext import bridge, tasks  # type: ignore
from loguru import logger

from enums import Loop, SearchPlatform, Shuffle

from . import Player_utils as plUtils
from .Queue import Queue
from .Track import Track, TrackInfo


def notify_and_close_condition(cond: Condition):
    with cond:
        cond.notify_all()


class Player(discord.VoiceClient):
    # TODO: Сделать работу с плейлистами (вроде изи)
    def __init__(self, client: bridge.Bot, channel: discord.VoiceChannel):
        super().__init__(client, channel)
        self.disconnect_timeout.start()
        self.__queue: Queue = Queue()
        self._playing_track = None

    @property
    def has_track(self) -> bool:
        return self.is_playing() or self.is_paused()

    @property
    def track(self) -> Optional[Track]:
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

    def set_settings(self, looping: Loop, shuffle: Shuffle):
        self.__queue.looping = looping
        self.__queue.shuffle = shuffle

    @tasks.loop(seconds=1)
    async def play_music(self):
        if self.__queue.current_track is None:
            self._playing_track = None
            self.play_music.cancel()
        if self.__queue.new_track:
            self._playing_track = await self.track.copy()
            asyncio.create_task(self.play_next())

    async def play_next(self):
        cond = Condition()

        def _wait_for_end(cond: Condition) -> None:
            with cond:
                cond.wait()
                self.__queue.update_queue()

        self.play(
            self._playing_track.src, after=lambda x: notify_and_close_condition(cond)
        )
        self.__queue.new_track = False
        self.pause()
        await asyncio.sleep(1)
        self.resume()
        Thread(target=_wait_for_end, args=(cond,)).start()

    def stop(self):
        if self.has_track:
            self.__queue.clear()
            super().stop()

    def toggle(self):
        if self.is_playing():
            self.pause()
        elif self.is_paused():
            self.resume()

    def skip(self):
        if self.has_track:
            super().stop()

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
        self, tracks_all_meta: list[Optional[TrackInfo]]
    ) -> None:
        if tracks_all_meta is None:
            logger.error("No tracks to add to queue")
            return
        for track_all_meta in tracks_all_meta:
            if not track_all_meta:
                continue
            await self.__queue.add_track(await Track.from_dict(track_all_meta))
            logmessage = "TRACKS QUEUE:"
            for track in self.__queue:
                logmessage += "\n" + str(track)
            logger.opt(colors=True).info(logmessage)
            if not self.has_track:
                self.play_music.start()

    @tasks.loop(seconds=5)
    async def disconnect_timeout(self):
        c = 0
        while not self.has_track:
            await asyncio.sleep(1)
            c += 1
            if self.has_track:
                break
            elif c == 60:
                await self.disconnect()

    def __del__(self):
        self.play_music.cancel()
        self.disconnect_timeout.cancel()
