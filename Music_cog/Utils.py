

from typing import Optional

import discord
from loguru import logger

from enums import ThreadType
from MongoDB import DataBase


def get_music_room(guild: Optional[discord.Guild]) -> Optional[discord.TextChannel]:
    room_id = DataBase().get_music_room_id(guild) if guild else None
    if room_id:
        room = guild.get_channel(room_id)  # type: ignore
        return room if isinstance(room, discord.TextChannel) else None
    logger.warning("NO MUSIC ROOM")
    return None

def get_thread(
    guild: discord.Guild, thread_type: ThreadType
) -> Optional[discord.Thread]:
    threads_ids = DataBase().get_threads_ids(guild)
    if threads_ids is not None:
        return guild.get_thread(threads_ids[thread_type])
    logger.warning("NO THREAD")
    return None