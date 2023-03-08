from enum import Enum
from typing import Any, Self


class Configuration(Enum):
    DEV: str = "dev"
    PROD: str = "prod"

    @classmethod
    def get_key(cls, config: str | Any) -> Self:
        for conf in cls:
            if conf.value == config:
                return conf
        return cls["DEV"]


class Loop(Enum):
    NOLOOP = "No Loop"
    LOOP = "Loop"
    ONE = "Loop One"

    @classmethod
    def get_key(cls, looping: str | Any) -> Self:
        for loop in cls:
            if loop.value == looping:
                return loop
        return cls["NOLOOP"]


class Shuffle(Enum):
    NOSHUFFLE: str = "No Shuffle"
    SHUFFLE: str = "Shuffle"
    SECRET: str = "Secret Shuffle"

    @classmethod
    def get_key(cls, shuffle: str | Any) -> Self:
        for shuf in cls:
            if shuf.value == shuffle:
                return shuf
        return cls["NOSHUFFLE"]


class ThreadType(Enum):
    QUEUE: str = "queue_id"
    SETTINGS: str = "settings_id"

    @classmethod
    def get_key(cls, thread_type: str | Any) -> Self | None:
        for thread in cls:
            if thread.value == thread_type:
                return thread
        return None


class SearchPlatform(Enum):
    YOUTUBE: str = "yt"
    VK: str = "vk"
    SPOTIFY: str = "spotify"
    SOUNDCLOUD: str = "soundcloud"

    @classmethod
    def get_key(cls, platform: str | Any) -> Self:
        for plat in cls:
            if plat.value == platform:
                return plat
        return cls["YOUTUBE"]
