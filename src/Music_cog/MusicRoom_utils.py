import discord
from discord.ext import bridge

import MongoDB as mdb
from config import get_config
from enums import ThreadType
from MongoDB import DataBase, MusicRoomInfo

from . import Utils
from .room.Embeds import EmbedDefault
from .room.Views import PlayerView, SettingsView


async def update_music_rooms_db(client: bridge.Bot):
    db = DataBase()
    guilds = client.guilds
    for guild in guilds:
        info = check_room_correctness(guild, db.music_rooms_collection)
        if not info:
            info = await create_music_room(client, guild)
        db.update_room_info(info)


def check_room_correctness(guild: discord.Guild, coll) -> MusicRoomInfo | None:
    info: MusicRoomInfo = coll.find_one({"guild_id": guild.id}, {"_id": 0, "guild_id": 1, "room_id": 1, "threads": 1})
    if info is not None:
        guild_channel = guild.get_channel(info["room_id"])
        music_room: discord.TextChannel | None = guild_channel if isinstance(guild_channel, discord.TextChannel) else None
        if music_room is None:
            return None

        for thread_key, thread_id in info["threads"].items():
            if (
                isinstance(thread_key, str)
                and not ThreadType.get_key(thread_key)
                or thread_id not in (thread.id for thread in music_room.threads)
            ):
                return None

        return mdb.convert_music_room_info(info, for_storage=False)
    return None


async def create_music_room(client: bridge.Bot, guild: discord.Guild) -> mdb.MusicRoomInfo:
    old_room = Utils.get_music_room(guild)
    if old_room:
        await old_room.delete()
    room = await guild.create_text_channel(name=get_config().get("ROOM_NAME", "Missing-name"), position=0)
    threads = await create_threads(client, room)
    view = PlayerView()
    message = await room.send(
        embed=EmbedDefault(guild),
        view=view,
    )
    client.add_view(view, message_id=message.id)
    await room.send("Channel Created", delete_after=5)
    return DataBase.create_music_room_info(guild, room, threads)


async def create_threads(client: bridge.Bot, room: discord.TextChannel) -> list[tuple[ThreadType, int]]:
    threads_ids = []
    for thread_type in ThreadType:
        thread = await room.create_thread(
            name=thread_type.name,
            type=discord.ChannelType.public_thread,
            auto_archive_duration=10080,
        )
        thread.slowmode_delay = 21600
        match thread_type:
            case ThreadType.SETTINGS:
                view = SettingsView()
                message = await thread.send(content="Search Platform", view=view)
                client.add_view(view, message_id=message.id)
        threads_ids.append((thread_type, thread.id))
    return threads_ids
