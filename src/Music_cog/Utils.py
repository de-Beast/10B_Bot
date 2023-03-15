from typing import TYPE_CHECKING

import discord
from discord.ext import commands, bridge
from loguru import logger
from MongoDB import DataBase
import Music_cog.player.Player as plr

if TYPE_CHECKING:
    from enums import ThreadType


def is_connected(user_bot_same_voice: bool = True):
    async def predicate(ctx: bridge.BridgeExtContext | bridge.BridgeApplicationContext) -> bool:
        return (
            ctx.author.voice is not None
            and ((isinstance(ctx.voice_client, plr.MusicPlayer) and ctx.author.voice.channel == ctx.voice_client.channel)
                 or not user_bot_same_voice)
        )

    return commands.check(predicate) # type: ignore


def get_music_room(guild: discord.Guild | None) -> discord.TextChannel | None:
    room_id = DataBase().get_music_room_id(guild) if guild else None
    if room_id and guild:
        room = guild.get_channel(room_id)
        return room if isinstance(room, discord.TextChannel) else None
    logger.warning("NO MUSIC ROOM OR GUILD")
    return None


def get_thread(guild: discord.Guild | None, thread_type: "ThreadType") -> discord.Thread | None:
    threads_ids = DataBase().get_threads_ids(guild) if guild else None
    if threads_ids and guild:
        return guild.get_thread(threads_ids[thread_type])
    logger.warning("NO THREAD")
    return None
