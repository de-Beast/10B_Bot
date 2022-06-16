from enum import Enum
from typing import Optional


class Loop(Enum):
    NOLOOP = "No Loop"
    LOOP = "Loop"
    ONE = "Loop One"
    
    @classmethod
    def get_key(cls, looping: str) -> "Loop":
        loop = [loop for loop in cls if loop.value == looping][0]
        return loop if loop else cls.NOLOOP


class Shuffle(Enum):
    NOSHUFFLE = "No Shuffle"
    SHUFFLE = "Shuffle"
    SECRET = "Secret Shuffle"
    
    @classmethod
    def get_key(cls, shuffle: str) -> "Shuffle":
        shuf = [loop for loop in cls if loop.value == shuffle][0]
        return shuf if shuf else cls.NOSHUFFLE


class ThreadType(Enum):
    SETTINGS: str = "settings_id"
    QUEUE: str = "queue_id"

    @classmethod
    def get_key(cls, thread_type: str) -> Optional["ThreadType"]:
        return [thread for thread in cls if thread.value == thread_type][0] # type: ignore


class SearchPlatform(Enum):
    YOUTUBE: str = "yt"
    VK: str = "vk"
    SPOTIFY: str = "spotify"
    SOUNDCLOUD: str = "soundcloud"

    @classmethod
    def get_key(cls, platform: str) -> "SearchPlatform":
        plat: SearchPlatform = [plat for plat in cls if plat.value == platform][0]
        return plat if plat else cls.YOUTUBE
