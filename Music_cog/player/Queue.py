from collections import deque
from typing import Optional

import discord

from enums import Loop, Shuffle

from .Track import Track, TrackInfo


class Queue(deque):
    def __init__(self):
        super().__init__()
        self.__current_track: Optional[Track] = None
        self.new_track: bool = False

        self.__looping: Loop = Loop.NOLOOP
        self.__shuffle: Shuffle = Shuffle.NOSHUFFLE

    @property
    def current_track(self) -> Optional[Track]:
        return self.__current_track

    @property
    def looping(self) -> Loop:
        return self.__looping

    @looping.setter
    def looping(self, loop_type: Loop):
        if isinstance(loop_type, Loop):
            self.__looping = loop_type
        else:
            raise TypeError("Loop type must be Loop enum")

    @property
    def shuffle(self) -> Shuffle:
        return self.__shuffle

    @shuffle.setter
    def shuffle(self, shuffle_type: Shuffle):
        if isinstance(shuffle_type, Shuffle):
            self.__shuffle = shuffle_type
        else:
            raise TypeError("Shuffle type must be Shuffle enum")

    def clear(self):
        super().clear()
        self.__current_track = None

    async def add_track(self, track_all_meta: TrackInfo):
        track = await Track.from_dict(track_all_meta)
        if track is not None:
            if self.__current_track is None:
                self.__current_track = track
                self.new_track = True
            else:
                self.append(track)

    def update_queue(self):
        try:
            match self.__looping:
                case Loop.NOLOOP:
                    self.__current_track = self.popleft()
                case Loop.LOOP:
                    self.append(self.__current_track)
                    self.__current_track = self.popleft()
            self.new_track = True
        except IndexError:
            self.__current_track = None
            self.new_track = False
        print(*self)
