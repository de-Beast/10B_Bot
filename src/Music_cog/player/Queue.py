import asyncio
import itertools
import random
import typing
from collections import deque
from enum import Enum

import discord
from discord.ext import bridge

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
    def __init__(self, client: bridge.Bot, guild: discord.Guild) -> None:
        super().__init__(self)
        self._current_index = 0

        self.client = client
        self.guild = guild

        self._looping: Loop = Loop.NOLOOP
        self._is_started = False

    async def init(self) -> None:
        if player_handler := await PlayerMessageHandler.from_room(
            Utils.get_music_room(self.guild)
        ):
            self._looping = player_handler.loop

    @property
    def is_started(self) -> bool:
        return self._is_started

    @property
    def current_index(self) -> int:
        return self._current_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        if len(self) == 0:
            self._current_index = 0
            return
        self._current_index = value % self.__len__()

    async def add_track(self, track: Track):
        self.append(track)

    def clear(self) -> None:
        super().clear()
        self.current_index = 0
        self._is_started = False

    def _change_index(self, step: int) -> None:
        self.current_index = self.current_index + step

    def next(self, *, force=False) -> Track | None:
        match self._looping:
            case Loop.NOLOOP:
                if force:
                    self._change_index(1)
                elif self.current_index == len(self) - 1:
                    return None
                else:
                    self._change_index(1)
            case Loop.ONE:
                if force:
                    self._change_index(1)
            case Loop.LOOP:
                self._change_index(1)
        self._is_started = False
        return self.current()

    def prev(self) -> Track | None:
        match self._looping:
            case Loop.NOLOOP:
                if self.current_index != 0:
                    self._change_index(-1)
            case Loop.LOOP:
                self._change_index(-1)
        return self.current()

    def current(self) -> Track | None:
        if len(self) == 0:
            return None
        if not self._is_started:
            self._is_started = True
        return self[self.current_index]


class Queue(SimpleQueue):
    def __init__(self, client: bridge.Bot, guild: discord.Guild) -> None:
        super().__init__(client, guild)
        self.__shuffled_queue: SimpleQueue = SimpleQueue(client, guild)
        self.__shuffle: Shuffle = Shuffle.NOSHUFFLE

    def __getitem__(self, __key: typing.SupportsIndex) -> typing.Any:  # type: ignore
        match self.shuffle:
            case Shuffle.NOSHUFFLE:
                return super().__getitem__(__key)
            case Shuffle.SHUFFLE:
                return self.__shuffled_queue[__key]

    @property
    def is_started(self) -> bool:
        match self.shuffle:
            case Shuffle.NOSHUFFLE:
                return super().is_started
            case Shuffle.SHUFFLE:
                return self.__shuffled_queue.is_started

    @property
    def current_index(self) -> int:
        match self.shuffle:
            case Shuffle.NOSHUFFLE:
                return super().current_index
            case Shuffle.SHUFFLE:
                return self.__shuffled_queue.current_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        match self.shuffle:
            case Shuffle.NOSHUFFLE:
                SimpleQueue.current_index.fset(self, value) # type: ignore
            case Shuffle.SHUFFLE:
                self.__shuffled_queue.current_index = value

    async def init(self) -> None:
        await super().init()
        await self.__shuffled_queue.init()
        if queue_handler := self._queue_handler:
            await queue_handler.remove_track_message(all=True)

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

    @property
    def looping(self) -> Loop:
        return self._looping

    @looping.setter
    def looping(self, looping: Loop):
        if isinstance(looping, Loop):
            self._looping = looping
            self.__shuffled_queue._looping = looping
        else:
            raise TypeError("Loop type must be Loop enum")

    @property
    def shuffle(self) -> Shuffle:
        return self.__shuffle

    async def set_shuffle(self, shuffle_type: Shuffle):
        if isinstance(shuffle_type, Shuffle):
            match shuffle_type:
                case Shuffle.SHUFFLE:
                    self.__shuffled_queue.clear()
                    self.__shuffled_queue.extend(self)
                    self.__shuffled_queue.remove(self.current())
                    random.shuffle(self.__shuffled_queue)
                    self.__shuffled_queue.appendleft(self.current())

                    if handler := self._queue_handler:
                        await handler.remove_track_message(all=True)
                        for index, track in enumerate(self.__shuffled_queue):
                            await handler.send_track_message(track, index + 1)
                case Shuffle.NOSHUFFLE:
                    if len(self.__shuffled_queue) > 0:
                        self.__shuffled_queue.clear()
                        if handler := self._queue_handler:
                            await handler.remove_track_message(all=True)
                            for index, track in enumerate(self):
                                await handler.send_track_message(track, index + 1)
            self.__shuffle = shuffle_type
        else:
            raise TypeError("Shuffle type must be Shuffle enum")

    async def clear(self):
        super().clear()
        if handler := self._queue_handler:
            await handler.remove_track_message(all=True)
        if self.__shuffle is not Shuffle.NOSHUFFLE:
            self.__shuffled_queue.clear()
            self.__shuffle = Shuffle.NOSHUFFLE

    async def add_track(self, track: Track):
        await super().add_track(track)
        if self.__shuffle is Shuffle.SHUFFLE:
            await self.__shuffled_queue.add_track(track)
        if queue_handler := self._queue_handler:
            await queue_handler.send_track_message(track, len(self))
        if history_handler := self._history_handler:
            await history_handler.store_track_in_history(track)
