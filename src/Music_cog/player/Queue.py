import asyncio
import random
from collections import deque

import discord
from enums import Loop, Shuffle, ThreadType

from Music_cog import Utils
from Music_cog.room import Handlers

from .Track import Track


class SimpleQueue(deque):
    def __init__(self, guild: discord.Guild) -> None:
        super().__init__()
        self._handler = Handlers.QueueThreadHandler(Utils.get_thread(guild, ThreadType.QUEUE))

        self._current_track: Track | None = None
        self.new_track: bool = False

        self._looping: Loop = Loop.NOLOOP

    def clear(self):
        super().clear()
        self._current_track = None
        self.new_track = False

    async def add_track(self, track: Track):
        if track is not None:
            if self._current_track is None:
                self._current_track = track
                self.new_track = True
            else:
                await self._handler.send_track_message(track, self.__len__() + 1)
                self.append(track)

    def prepare_prev_track(self):
        if self._looping is not Loop.ONE:
            self.appendleft(self._current_track)
            if self._looping is Loop.LOOP:
                self.rotate(1)
            self._current_track = None

    async def update_queue(self, loop: asyncio.AbstractEventLoop | None = None):
        try:
            match self._looping:
                case Loop.NOLOOP:
                    self._current_track = self.popleft()
                    if loop:
                        loop.create_task(self._handler.remove_track_message())
                case Loop.LOOP:
                    if self._current_track is not None:
                        self.append(self._current_track)
                        if loop and self.__len__() > 1:
                            loop.create_task(
                                self._handler.send_track_message(self._current_track, self.__len__() - 1, is_loop=True)
                            )
                    self._current_track = self.popleft()
            self.new_track = True
        except IndexError:
            self._current_track = None
            self.new_track = False


class Queue(SimpleQueue):
    def __init__(self, guild: discord.Guild):
        super().__init__(guild)
        self.__shuffled_queue: SimpleQueue = SimpleQueue(guild)
        self.__shuffle: Shuffle = Shuffle.NOSHUFFLE
        self.is_shuffled: bool = False

    @property
    def looping(self) -> Loop:
        return self._looping

    @looping.setter
    def looping(self, loop_type: Loop):
        if isinstance(loop_type, Loop):
            self._looping = loop_type
            self.__shuffled_queue._looping = loop_type
        else:
            raise TypeError("Loop type must be Loop enum")

    @property
    def shuffle(self) -> Shuffle:
        return self.__shuffle

    @shuffle.setter
    def shuffle(self, shuffle_type: Shuffle):
        if isinstance(shuffle_type, Shuffle):
            self.__shuffle = shuffle_type
            if shuffle_type is not Shuffle.NOSHUFFLE:
                self.__shuffled_queue.clear()
                self.__shuffled_queue._current_track = self._current_track
                self.__shuffled_queue.extend(self)
                random.shuffle(self.__shuffled_queue)
                self.is_shuffled = True
        else:
            raise TypeError("Shuffle type must be Shuffle enum")

    @property
    def current_track(self) -> Track | None:
        if self.__shuffle is not Shuffle.NOSHUFFLE:
            return self.__shuffled_queue._current_track
        return self._current_track

    async def clear(self):
        super().clear()
        await self._handler.remove_track_message(all=True)
        if self.__shuffle is not Shuffle.NOSHUFFLE:
            self.__shuffled_queue.clear()
            self.__shuffle = Shuffle.NOSHUFFLE

    async def add_track(self, track: Track, *args):
        await super().add_track(
            track,
        )
        if self.__shuffle is not Shuffle.NOSHUFFLE:
            await self.__shuffled_queue.add_track(track)

    def prepare_prev_track(self):
        if self.__shuffle is not Shuffle.NOSHUFFLE:
            self.__shuffled_queue.prepare_prev_track()
        else:
            super().prepare_prev_track()

    async def update_queue(self, loop: asyncio.AbstractEventLoop | None = None, *args):
        match self.__shuffle:
            case Shuffle.NOSHUFFLE:
                if len(self.__shuffled_queue) > 0:
                    self.__shuffled_queue.clear()
                await super().update_queue(loop)
            case Shuffle.SHUFFLE | Shuffle.SECRET as shuffle:
                if not self.is_shuffled:
                    random.shuffle(self.__shuffled_queue)
                    self.is_shuffled = True

                await self.__shuffled_queue.update_queue()
                await super().update_queue(loop)
                self.append(self._current_track)
                self._current_track = None
                try:
                    self.rotate(-1 * self.index(self.__shuffled_queue._current_track))
                except ValueError:
                    self.__shuffle = Shuffle.NOSHUFFLE
                await super().update_queue(loop)
                if shuffle is Shuffle.SECRET:
                    self.is_shuffled = False
