from enum import Enum
from typing import Self


class Configuration(Enum):
    DEV: str = "dev"
    PROD: str = "prod"

    @classmethod
    def get_key(cls, config: str) -> Self:  # type: ignore[valid-type]
        conf = [c for c in cls if c.value == config][0]
        return conf if conf else cls.DEV


class Loop(Enum):
    NOLOOP = "No Loop"
    LOOP = "Loop"
    ONE = "Loop One"

    @classmethod
    def get_key(cls, looping: str) -> Self:  # type: ignore[valid-type]
        loop = [loop for loop in cls if loop.value == looping][0]
        return loop if loop else cls.NOLOOP


class Shuffle(Enum):
    NOSHUFFLE: str = "No Shuffle"
    SHUFFLE: str = "Shuffle"
    SECRET: str = "Secret Shuffle"

    @classmethod
    def get_key(cls, shuffle: str) -> Self:  # type: ignore[valid-type]
        shuf = [shuf for shuf in cls if shuf.value == shuffle][0]
        return shuf if shuf else cls.NOSHUFFLE


class ThreadType(Enum):
    QUEUE: str = "queue_id"
    SETTINGS: str = "settings_id"

    @classmethod
    def get_key(cls, thread_type: str) -> Self | None:  # type: ignore[valid-type]
        return [thread for thread in cls if thread.value == thread_type][0]


class SearchPlatform(Enum):
    YOUTUBE: str = "yt"
    VK: str = "vk"
    SPOTIFY: str = "spotify"
    SOUNDCLOUD: str = "soundcloud"

    @classmethod
    def get_key(cls, platform: str) -> Self:  # type: ignore[valid-type]
        plat: SearchPlatform = [plat for plat in cls if plat.value == platform][0]
        return plat if plat else cls.YOUTUBE
