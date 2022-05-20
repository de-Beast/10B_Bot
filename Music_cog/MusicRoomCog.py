import json

import discord
from discord.ext import commands, tasks

from config import settings
from Music_cog.player.Player import Player

from .room.Handlers import MainMessageHandler, ThreadMessageHandler

MUSIC_ROOMS_FILE_JSON = "Music_cog/Music_rooms.json"
MUSIC_ROOMS_DICTS = []


def update_music_rooms_dicts():
    MUSIC_ROOMS_DICTS.clear()
    with open(MUSIC_ROOMS_FILE_JSON, "r") as f:
        data = json.load(f)
        for info in data:
            MUSIC_ROOMS_DICTS.append(info)


def create_music_room_info(
    guild: discord.Guild, music_room: discord.TextChannel, threads: list
):
    info = {"guild_id": guild.id, "room_id": music_room.id, "threads": {}}
    for thread in threads:
        info["threads"][thread[0]] = thread[1]
    print(f"{guild} (id: {guild.id}) Updated Music Room!!! - new id: {music_room.id}")
    return info


async def update_music_rooms_db(client: commands.Bot, rooms: list = None):
    update_music_rooms_dicts()
    if rooms is None:
        rooms = []
    guilds = client.guilds
    for guild in guilds:
        info = check_room_correctness(guild)
        if not info:
            info = await create_music_room(client, guild)
        rooms.append(info)
    f = open(MUSIC_ROOMS_FILE_JSON, "w")
    json.dump(rooms, f, indent=3)
    f.close()
    update_music_rooms_dicts()


def check_room_correctness(guild: discord.Guild) -> dict | bool:
    for info in MUSIC_ROOMS_DICTS:
        if guild.id == info["guild_id"]:
            room = guild.get_channel(info["room_id"])
            if room is None:
                return False

            threads_ids = list(info["threads"].values())
            if threads_ids == []:
                return False

            for thread in room.threads:
                if thread.id not in threads_ids:
                    return False

            return info
    return False


def get_music_room(guild: discord.Guild) -> discord.TextChannel:
    for info in MUSIC_ROOMS_DICTS:
        if guild.id == info["guild_id"]:
            return guild.get_channel(info["room_id"])
    print("NO CHANNEL FOR U")
    return None


def get_thread(guild: discord.Guild, thread_type: str) -> discord.Thread:
    for info in MUSIC_ROOMS_DICTS:
        if guild.id == info["guild_id"]:
            return guild.get_thread(info["threads"][thread_type])
    print("NO THREAD FOR U")
    return None


async def create_music_room(client: commands.Bot, guild: discord.Guild):
    if get_music_room(guild):
        await get_music_room(guild).delete()
    room = await guild.create_text_channel(name=settings["room_name"], position=0)
    threads = await create_threads(client, room)
    await room.send(
        file=MainMessageHandler.create_file(),
        embed=MainMessageHandler.create_embed(),
        view=MainMessageHandler.create_main_view(client),
    )
    await room.send("Channel Created", delete_after=5)
    return create_music_room_info(guild, room, threads)


async def create_threads(client: commands.Bot, room: discord.TextChannel) -> list:
    threads = [("settings_id", "Settings"), ("queue_id", "Queue")]
    threads_ids = []
    for thread_info in threads:
        thread = await room.create_thread(
            name=thread_info[1],
            type=discord.ChannelType.public_thread,
            auto_archive_duration=10080,
        )
        thread.slowmode_delay = 21600
        if thread_info[1] == "Settings":
            await thread.send(
                content="Search Platform",
                view=ThreadMessageHandler.create_settings_view(client),
            )
        threads_ids.append((thread_info[0], thread.id))
    return threads_ids


class MusicRoomCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client

    @tasks.loop(seconds=1)
    async def display_playing_track(self, room: discord.TextChannel, player: Player):
        try:
            track = player.get_track()
        except Exception:
            track = None
        if self.display_playing_track.track != track:
            self.display_playing_track.track = track
            handler = await MainMessageHandler.init(room)
            await handler.update_embed(track)

    @commands.command(name="delete")
    async def delete(self, ctx: commands.Context):
        await ctx.channel.delete()

    @commands.command(
        name="create_music_room",
        aliases=["create", "make_room", "create_room", "make_music_room"],
    )
    @commands.check_any(
        commands.is_owner(), commands.has_guild_permissions(administrator=True)
    )
    async def create_music_room_command(self, ctx: commands.Context):
        room_info = await create_music_room(self.client, ctx.guild)
        await update_music_rooms_db(self.client, [room_info])

    @commands.command(name="clear_room", aliases=["clear", "c"])
    @commands.cooldown(3, 5)
    async def clear_room(self, ctx: commands.Context):
        room = get_music_room(ctx.guild)
        try:
            while len(await room.history(oldest_first=True).flatten()) > 3:
                try:
                    await room.purge(check=lambda m: m.author != self.client.user)
                except Exception:
                    print("Deleting messages error")
        except Exception:
            print("Unknown Channel")

    ############ Listeners ############

    @commands.Cog.listener("on_guild_join")
    async def on_guild_join(self, guild: discord.Guild):
        await update_music_rooms_db(self.client)

    @commands.Cog.listener("on_guild_remove")
    async def on_guild_remove(self, guild: discord.Guild):
        await update_music_rooms_db(self.client)

    @commands.Cog.listener("on_message")
    async def play_music_on_message(self, message: discord.Message):
        if not message.author.bot:
            if message.channel == get_music_room(
                message.guild
            ) and not message.content.startswith(
                settings["prefix"], 0, len(settings["prefix"])
            ):
                ctx = await self.client.get_context(message)
                await ctx.invoke(self.client.get_command("play"), message.content)

    @commands.Cog.listener("on_message")
    async def clear_music_room(self, message: discord.Message):
        if message.channel == get_music_room(message.guild) and not message.author.bot:
            await self.clear_room(await self.client.get_context(message))

    @commands.Cog.listener("on_ready")
    async def check_music_rooms_in_guilds(self):
        await update_music_rooms_db(self.client)
        for guild in self.client.guilds:
            try:
                handler = await MainMessageHandler.init(get_music_room(guild), self.client)
                await handler.update_main_view()
                await handler.update_embed()
                for thread_type in ("settings_id", "queue_id"):
                    await ThreadMessageHandler(
                        get_thread(guild, thread_type), self.client
                    ).update_threads_views()
            except Exception:
                break
        await self.client.when_ready()

    @commands.Cog.listener("on_voice_state_update")
    async def binding_playing_track_view(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.id == self.client.user.id and before.channel != after.channel:
            if after.channel is not None:
                try:
                    player: Player = member.guild.voice_client
                except Exception as e:
                    print(e)
                self.display_playing_track.track = None
                self.display_playing_track.start(get_music_room(member.guild), player)
            else:
                self.display_playing_track.cancel()
                handler = await MainMessageHandler.init(
                    get_music_room(member.guild),
                )
                await handler.update_embed()


def setup(client: commands.Bot):
    client.add_cog(MusicRoomCog(client))
