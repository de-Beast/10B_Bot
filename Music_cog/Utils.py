from typing import TYPE_CHECKING

import discord
from loguru import logger

from MongoDB import DataBase

if TYPE_CHECKING:
    from enums import ThreadType

def get_music_room(guild: discord.Guild | None) -> discord.TextChannel | None:
    room_id = DataBase().get_music_room_id(guild) if guild else None
    if room_id:
        room = guild.get_channel(room_id)  # type: ignore
        return room if isinstance(room, discord.TextChannel) else None
    logger.warning("NO MUSIC ROOM")
    return None

def get_thread(guild: discord.Guild, thread_type: "ThreadType") -> discord.Thread | None:
    threads_ids = DataBase().get_threads_ids(guild)
    if threads_ids is not None:
        return guild.get_thread(threads_ids[thread_type])
    logger.warning("NO THREAD")
    return None