import random
from collections import deque
from typing import Optional

import discord

from enums import Loop, Shuffle

from .Track import Track, TrackInfo


class SimpleQueue(deque):
    def __init__(self):
        super().__init__()
        self._current_track: Optional[Track] = None
        self.new_track: bool = False

        self._looping: Loop = Loop.NOLOOP


    def clear(self):
        super().clear()
        self._current_track = None

    async def add_track(self, track: Track):
        if track is not None:
            if self._current_track is None:
                self._current_track = track
                self.new_track = True
            else:
                self.append(track)

    def update_queue(self):
        try:
            match self._looping:
                case Loop.NOLOOP:
                    self._current_track = self.popleft()
                case Loop.LOOP:
                    if self._current_track is not None:
                        self.append(self._current_track)
                    self._current_track = self.popleft()
            self.new_track = True
        except IndexError:
            self._current_track = None
            self.new_track = False


class Queue(SimpleQueue):
    def __init__(self):
        super().__init__()
        self.__shuffled_queue: SimpleQueue = SimpleQueue()
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
    def current_track(self) -> Optional[Track]:
        if self.__shuffle is not Shuffle.NOSHUFFLE:
            return self.__shuffled_queue._current_track
        return self._current_track

    def clear(self):
        super().clear()
        if self.__shuffle is not Shuffle.NOSHUFFLE:
            self.__shuffled_queue.clear()
            self.__shuffle = Shuffle.NOSHUFFLE

    async def add_track(self, track: Track):
        await super().add_track(track)
        if self.__shuffle is not Shuffle.NOSHUFFLE:
            await self.__shuffled_queue.add_track(track)

    def update_queue(self):
        match self.__shuffle:
            case Shuffle.NOSHUFFLE:
                if len(self.__shuffled_queue) > 0:
                    self.__shuffled_queue.clear()
                super().update_queue()
            case Shuffle.SHUFFLE | Shuffle.SECRET as shuffle:
                if not self.is_shuffled:
                    random.shuffle(self.__shuffled_queue)
                    self.is_shuffled = True

                self.__shuffled_queue.update_queue()
                super().update_queue()
                self.append(self._current_track)
                self._current_track = None
                try:
                    self.rotate(-1 * self.index(
                            self.__shuffled_queue._current_track
                            )
                        )
                except ValueError:
                    self.__shuffle = Shuffle.NOSHUFFLE
                super().update_queue()
                if shuffle is Shuffle.SECRET:
                    self.is_shuffled = False