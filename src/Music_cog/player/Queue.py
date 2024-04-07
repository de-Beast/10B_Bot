import random
import typing
from collections import deque
from enum import Enum

import discord
from discord.ext import bridge

from enums import Loop, Shuffle
from Music_cog.room.Handlers import (
    HistoryThreadHandler,
    PlayerMessageHandler,
    QueueThreadHandler,
)

from .Track import Track


class SimpleQueue(deque):
    class State(Enum):
        START = 0
        RUNNING = 1
        END = 2

    def __init__(self, client: bridge.Bot, guild: discord.Guild) -> None:
        super().__init__(self)
        self._current_index = 0

        self.client = client
        self.guild = guild

        self._looping: Loop = Loop.NOLOOP
        self._state = SimpleQueue.State.START

    async def init(self) -> None:
        if player_handler := await PlayerMessageHandler.from_guild_async(self.guild):
            self._looping = player_handler.loop

    @property
    def state(self) -> "SimpleQueue.State":
        return self._state

    @state.setter
    def state(self, value: "SimpleQueue.State") -> None:
        self._state = value

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

    async def remove_track(self, track: Track | None = None):
        if track is None:
            track = self._current()
        self.remove(track)

    def clear(self) -> None:
        super().clear()
        self.current_index = 0
        self.state = SimpleQueue.State.START

    def _change_index(self, step: int) -> None:
        self.current_index = self.current_index + step

    def next(self, *, force=False) -> Track | None:
        match self._looping:
            case Loop.NOLOOP:
                if force:
                    self._change_index(1)
                elif self.current_index == len(self) - 1:
                    self.state = SimpleQueue.State.END
                    return None
                else:
                    self._change_index(1)
            case Loop.ONE:
                if force:
                    self._change_index(1)
            case Loop.LOOP:
                self._change_index(1)
        return self._current(start=True)

    def prev(self) -> Track | None:
        self._change_index(-1)
        return self._current(start=True)

    def current(self) -> Track | None:
        return self._current(start=True)

    def _current(self, *, start: bool = False) -> Track | None:
        if len(self) == 0:
            return None
        if self.state is not SimpleQueue.State.RUNNING and start:
            self.state = SimpleQueue.State.RUNNING
        return self[self.current_index]


class Queue(SimpleQueue):
    def __init__(self, client: bridge.Bot, guild: discord.Guild) -> None:
        super().__init__(client, guild)
        self.__queue_handler: QueueThreadHandler | None = None
        self.__history_handler: HistoryThreadHandler | None = None

        self.__shuffled_queue: SimpleQueue = SimpleQueue(client, guild)
        self.__shuffle: Shuffle = Shuffle.NOSHUFFLE

    def __getitem__(self, __key: typing.SupportsIndex) -> typing.Any:  # type: ignore
        match self.shuffle:
            case Shuffle.NOSHUFFLE:
                return super().__getitem__(__key)
            case Shuffle.SHUFFLE:
                return self.__shuffled_queue[__key]

    @property
    def state(self) -> SimpleQueue.State:
        match self.shuffle:
            case Shuffle.NOSHUFFLE:
                return super().state
            case Shuffle.SHUFFLE:
                return self.__shuffled_queue.state

    @state.setter
    def state(self, value: SimpleQueue.State) -> None:
        match self.shuffle:
            case Shuffle.NOSHUFFLE:
                SimpleQueue.state.fset(self, value)  # type: ignore
            case Shuffle.SHUFFLE:
                self.__shuffled_queue.state = value

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
                SimpleQueue.current_index.fset(self, value)  # type: ignore
            case Shuffle.SHUFFLE:
                self.__shuffled_queue.current_index = value
                current = self._current()
                SimpleQueue.current_index.fset(  # type: ignore
                    self, self.index(current) if current else 0
                )

    def _change_index(self, step: int) -> None:
        prev_index = self.current_index
        super()._change_index(step)
        self.client.loop.create_task(self._update_current_track_in_thread(prev_index))

    async def init(self) -> None:
        await super().init()
        await self.__shuffled_queue.init()
        if queue_handler := self._queue_handler:
            await queue_handler.remove_track_message(all=True)

    @property
    def _queue_handler(self) -> QueueThreadHandler | None:
        if not self.__queue_handler:
            self.__queue_handler = QueueThreadHandler.from_guild(self.guild)
        if not self.__queue_handler or not QueueThreadHandler.check(
            self.__queue_handler
        ):
            return None

        return self.__queue_handler

    @property
    def _history_handler(self) -> HistoryThreadHandler | None:
        if not self.__history_handler:
            self.__history_handler = HistoryThreadHandler.from_guild(self.guild)
        if not self.__history_handler or HistoryThreadHandler.check(
            self.__history_handler
        ):
            return None
        return self.__history_handler

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

    def next(self, *, force=False) -> Track | None:
        next = super().next(force=force)
        if next is None:
            self.client.loop.create_task(
                self._update_current_track_in_thread(prev_index=self.current_index)
            )
        return next

    async def set_shuffle(self, shuffle_type: Shuffle):
        if isinstance(shuffle_type, Shuffle):
            match shuffle_type:
                case Shuffle.SHUFFLE:
                    state = self.state
                    self._setup_shuffled_queue()
                    self.__shuffle = shuffle_type
                    if state is SimpleQueue.State.END:
                        self.state = SimpleQueue.State.START
                    else:
                        self.state = state

                    await self._try_reload_queue_thread()
                case Shuffle.NOSHUFFLE:
                    state = self.state
                    self.__shuffled_queue.clear()
                    self.__shuffle = shuffle_type
                    if state is SimpleQueue.State.END:
                        self.state = SimpleQueue.State.START
                    else:
                        self.state = state
                    await self._try_reload_queue_thread()
        else:
            raise TypeError("Shuffle type must be Shuffle enum")

    async def _try_reload_queue_thread(self):
        if handler := self._queue_handler:
            await handler.remove_track_message(all=True)
            for index, track in enumerate(
                self.__shuffled_queue if self.shuffle is Shuffle.SHUFFLE else self
            ):
                await handler.send_track_message(
                    track, index, is_playing=track == self._current()
                )

    def _setup_shuffled_queue(self):
        self.__shuffled_queue.clear()
        self.__shuffled_queue.extend(self)
        shuffle = self.shuffle
        self.__shuffle = Shuffle.NOSHUFFLE
        self.__shuffled_queue.remove(self._current())
        random.shuffle(self.__shuffled_queue)
        self.__shuffled_queue.appendleft(self._current())
        self.__shuffle = shuffle

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
            await queue_handler.send_track_message(
                track, len(self) - 1, is_playing=track == self._current()
            )
        if history_handler := self._history_handler:
            await history_handler.store_track_in_history(track)

    async def _update_current_track_in_thread(self, prev_index: int | None = None):
        if queue_handler := self._queue_handler:
            if self.current_index != prev_index:
                await queue_handler.update_track_color(self.current_index)
            if prev_index is not None:
                await queue_handler.update_track_color(prev_index, is_playing=False)

    async def remove_track(self, track: Track | None = None):
        if track is None:
            track = self._current()
        await super().remove_track(track)
        if self.__shuffle is Shuffle.SHUFFLE:
            await self.__shuffled_queue.remove_track(track)
        if queue_handler := self._queue_handler:
            await queue_handler.remove_track_message(track)
    
    async def remove_track_by_message_id(self, message_id: int):
        await self.remove_track(await self._queue_handler.get_track_by_message_id(message_id))
