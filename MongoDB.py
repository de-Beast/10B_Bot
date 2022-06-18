from contextlib import contextmanager
from typing import Any, Literal, Optional, TypedDict, overload

import discord
import pymongo
from loguru import logger

from config import settings
from enums import ThreadType


class MusicRoomInfo(TypedDict):
    guild_id: int
    room_id: int
    threads: dict[ThreadType, int]


class StorageMusicRoomInfo(TypedDict):
    guild_id: int
    room_id: int
    threads: dict[str, int]


class DataBase:
    __instance: Optional["DataBase"] = None
    __database: Any = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__database = pymongo.MongoClient(settings["db_url"]).TenB_Bot
        return cls.__instance

    @property
    def music_rooms_collection(self):
        return self.__database.Music_rooms

    @staticmethod
    def create_music_room_info(
        guild: discord.Guild,
        music_room: discord.TextChannel,
        threads: list[tuple[ThreadType, int]],
    ) -> MusicRoomInfo:
        info = MusicRoomInfo(
            {"guild_id": guild.id, "room_id": music_room.id, "threads": {}}
        )
        for thread_type, id in threads:
            info["threads"][thread_type] = id
        logger.info(
            f"{guild} (id: {guild.id}) Updated Music Room!!! - new id: {music_room.id}"
        )
        return info

    def update_room_info(self, room_info: MusicRoomInfo):
        edited_info = convert_music_room_info(room_info)
        self.music_rooms_collection.update_one(
            {"guild_id": edited_info["guild_id"]}, {"$set": edited_info}, upsert=True
        )

    def get_music_room_id(self, guild: discord.Guild) -> int | None:
        info = self.music_rooms_collection.find_one(
            {"guild_id": guild.id}, {"_id": 0, "room_id": 1}
        )
        return info["room_id"] if info else None

    def get_threads_ids(self, guild: discord.Guild) -> dict[ThreadType, int] | None:
        info: dict[str, Any] = self.music_rooms_collection.find_one(
            {"guild_id": guild.id}, {"_id": 0, "threads": 1}
        )
        if info is not None:
            threads_ids: dict[str, int] = info["threads"]
            edited_info: dict[ThreadType, int] = {}
            for thread_type in ThreadType:
                try:
                    edited_info[thread_type] = threads_ids.pop(thread_type.value)
                except KeyError:
                    return None
            return edited_info


@overload
def convert_music_room_info(
    info: StorageMusicRoomInfo, *, for_storage: Literal[False]
) -> MusicRoomInfo:
    ...


@overload
def convert_music_room_info(
    info: MusicRoomInfo, *, for_storage: Literal[True] = True
) -> StorageMusicRoomInfo:
    ...


def convert_music_room_info(info, *, for_storage=True):
    if for_storage:
        converted_info: StorageMusicRoomInfo = {
            "guild_id": info["guild_id"],
            "room_id": info["room_id"],
            "threads": {thread.value: info["threads"][thread] for thread in ThreadType},
        }
        return converted_info

    else:
        converted_info: MusicRoomInfo = {
            "guild_id": info["guild_id"],
            "room_id": info["room_id"],
            "threads": {thread: info["threads"][thread.value] for thread in ThreadType},
        }
        return converted_info
