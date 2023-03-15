from enum import Enum
from typing import Any, Self


class Configuration(Enum):
    DEV: str = "dev"
    PROD: str = "prod"

    @classmethod
    def get_key(cls, config: str | Any) -> Self:
        for _config in cls:
            if _config.value == config:
                return _config
        return cls["DEV"]


class Loop(Enum):
    NOLOOP = "No Loop"
    LOOP = "Loop"
    ONE = "Loop One"

    @classmethod
    def get_key(cls, loop: str | Any) -> Self:
        for _loop in cls:
            if _loop.value == loop:
                return _loop
        return cls["NOLOOP"]


class Shuffle(Enum):
    NOSHUFFLE: str = "No Shuffle"
    SHUFFLE: str = "Shuffle"
    SECRET: str = "Secret Shuffle"

    @classmethod
    def get_key(cls, shuffle: str | Any) -> Self:
        for _shuffle in cls:
            if _shuffle.value == shuffle:
                return _shuffle
        return cls["NOSHUFFLE"]


class ThreadType(Enum):
    HISTORY: str = "history_id"
    SETTINGS: str = "settings_id"
    QUEUE: str = "queue_id"

    @classmethod
    def get_key(cls, thread_type: str | Any) -> Self | None:
        for _thread_type in cls:
            if _thread_type.value == thread_type:
                return _thread_type
        return None


class SearchPlatform(Enum):
    YOUTUBE: str = "Youtube"
    VK: str = "VK"
    SPOTIFY: str = "Spotify"
    SOUNDCLOUD: str = "Soundcloud"

    @classmethod
    def get_key(cls, platform: str | Any) -> Self:
        for _platform in cls:
            if _platform.value == platform:
                return _platform
        return cls["YOUTUBE"]
