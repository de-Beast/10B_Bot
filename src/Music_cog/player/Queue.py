import asyncio
import random
from collections import deque

import discord

from enums import Loop, Shuffle, ThreadType
from Music_cog import Utils
from Music_cog.room.Handlers import (
    HistoryThreadHandler,
    PlayerMessageHandler,
    QueueThreadHandler,
)

from .Track import Track

# TODO: Отображение очереди должно быть вместе с играющим треком. Играющий трек должен быть просто явно отмечен.
# Так не придется постоянно удалять треки из отображаемой очереди 
# Можно будет сделать более менее оптимизированную перемотку назад, 
# которая будет включать предыдущий трек, если очередь зациклена

class SimpleQueue(deque):
    def __init__(self, guild: discord.Guild) -> None:
        super().__init__()
        self.guild = guild
        self._current_track: Track | None = None
        self.new_track = False
        self._is_prev_track_prepared = False

        self._loop: Loop = Loop.NOLOOP

    async def init(self) -> None:
        if queue_handler := self._queue_handler:
            await queue_handler.remove_track_message(all=True)
        if player_handler := await PlayerMessageHandler.from_room(Utils.get_music_room(self.guild)):
            self._loop = player_handler.loop

    @property
    def _queue_handler(self) -> QueueThreadHandler | None:
        if thread := Utils.get_thread(self.guild, ThreadType.QUEUE):
            return QueueThreadHandler(thread)
        return None

    @property
    def _history_handler(self) -> HistoryThreadHandler | None:
        if thread := Utils.get_thread(self.guild, ThreadType.HISTORY):
            return HistoryThreadHandler(thread)
        return None

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
                if queue_handler := self._queue_handler:
                    await queue_handler.send_track_message(track, self.__len__() + 1)
                self.append(track)
            if history_handler := self._history_handler:
                await history_handler.store_track_in_history(track)

    def prepare_prev_track(self):
        self._is_prev_track_prepared = True

    async def update_queue(self, loop: asyncio.AbstractEventLoop | None = None):
        if self._is_prev_track_prepared:
            self._is_prev_track_prepared = False
            self.new_track = True
            return

        try:
            match self._loop:
                case Loop.NOLOOP:
                    self._current_track = self.popleft()
                    if loop and (queue_handler := self._queue_handler):
                        loop.create_task(queue_handler.remove_track_message())
                case Loop.LOOP:
                    if self._current_track is not None:
                        self.append(self._current_track)
                        if loop and self.__len__() > 1 and (queue_handler := self._queue_handler):
                            loop.create_task(
                                queue_handler.send_track_message(self._current_track, self.__len__() - 1, is_loop=True)
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

    @property
    def loop(self) -> Loop:
        return self._loop

    @loop.setter
    def loop(self, loop_type: Loop):
        if isinstance(loop_type, Loop):
            self._loop = loop_type
            self.__shuffled_queue._loop = loop_type
        else:
            raise TypeError("Loop type must be Loop enum")

    @property
    def shuffle(self) -> Shuffle:
        return self.__shuffle

    async def set_shuffle(self, shuffle_type: Shuffle):
        if isinstance(shuffle_type, Shuffle):
            self.__shuffle = shuffle_type
            match shuffle_type:
                case Shuffle.SHUFFLE:
                    self.__shuffled_queue.clear()
                    self.__shuffled_queue._current_track = self._current_track
                    self.__shuffled_queue.extend(self)
                    random.shuffle(self.__shuffled_queue)

                    if handler := self._queue_handler:
                        await handler.remove_track_message(all=True)
                        for index, track in enumerate(self.__shuffled_queue):
                            await handler.send_track_message(track, index + 1)
                case Shuffle.NOSHUFFLE:
                    if self.__shuffled_queue.__len__() > 0:
                        self.__shuffled_queue.clear()
                        if handler := self._queue_handler:
                            await handler.remove_track_message(all=True)
                            for index, track in enumerate(self):
                                await handler.send_track_message(track, index + 1)
        else:
            raise TypeError("Shuffle type must be Shuffle enum")

    @property
    def current_track(self) -> Track | None:
        if self.__shuffle is not Shuffle.NOSHUFFLE:
            return self.__shuffled_queue._current_track
        return self._current_track

    async def clear(self):
        super().clear()
        if handler := self._queue_handler:
            await handler.remove_track_message(all=True)
        if self.__shuffle is not Shuffle.NOSHUFFLE:
            self.__shuffled_queue.clear()
            self.__shuffle = Shuffle.NOSHUFFLE

    async def add_track(self, track: Track, *args):
        await super().add_track(track)
        if self.__shuffle is not Shuffle.NOSHUFFLE:
            await self.__shuffled_queue.add_track(track)

    def prepare_prev_track(self):
        if self.__shuffle is Shuffle.SHUFFLE:
            self.__shuffled_queue.prepare_prev_track()

        super().prepare_prev_track()

    async def update_queue(self, loop: asyncio.AbstractEventLoop | None = None, *args):
        if self._is_prev_track_prepared:
            self._is_prev_track_prepared = False
            self.new_track = True
            return

        match self.__shuffle:
            case Shuffle.NOSHUFFLE:
                if len(self.__shuffled_queue) > 0:
                    self.__shuffled_queue.clear()
                await super().update_queue(loop)
            case Shuffle.SHUFFLE:
                await self.__shuffled_queue.update_queue()
                await super().update_queue(loop)
                self.append(self._current_track)
                self._current_track = None
                try:
                    self.rotate(-1 * self.index(self.__shuffled_queue._current_track))
                except ValueError:
                    self.__shuffle = Shuffle.NOSHUFFLE
                await super().update_queue(loop)
