import discord
from discord.ext import bridge, commands
from loguru import logger
from pymongo.collection import Collection

import MongoDB as mdb
from ABC import CogABC
from Bot import TenB_Bot
from config import get_config
from enums import ThreadType
from MongoDB import DataBase, MusicRoomInfo
from Music_cog.room.Embeds import EmbedDefault
from Music_cog.room.Views.PlayerView import PlayerView
from Music_cog.room.Views.SettingsView import SettingsView

from . import Utils
from .room import Handlers
from .room.Handlers import PlayerMessageHandler


class MusicRoomCog(CogABC):
    @staticmethod
    def check_room_correctness(guild: discord.Guild, coll: Collection[MusicRoomInfo]) -> MusicRoomInfo | None:
        info: MusicRoomInfo | None = coll.find_one(
            {"guild_id": guild.id}, {"_id": 0, "guild_id": 1, "room_id": 1, "threads": 1}
        )
        if info is not None:
            guild_channel = guild.get_channel(info["room_id"])
            music_room: discord.TextChannel | None = (
                guild_channel if isinstance(guild_channel, discord.TextChannel) else None
            )
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

    async def update_music_rooms_db(self) -> None:
        db = DataBase()
        guilds = self.client.guilds
        for guild in guilds:
            info = self.check_room_correctness(guild, db.music_rooms_collection)
            if not info:
                info = await self.create_music_room(guild)
            db.update_room_info(info)

    async def create_music_room(self, guild: discord.Guild) -> mdb.MusicRoomInfo:
        old_room = Utils.get_music_room(guild)
        if old_room:
            await old_room.delete()
        room = await guild.create_text_channel(name=get_config().get("ROOM_NAME", "Missing-name"), position=0)
        threads = await self.create_threads(room)
        view = PlayerView()
        message = await room.send(
            embed=EmbedDefault(guild),
            view=view,
        )
        self.client.add_view(view, message_id=message.id)
        await room.send("Channel Created", delete_after=5)
        return DataBase.create_music_room_info(guild, room, threads)

    async def create_threads(self, room: discord.TextChannel) -> list[tuple[ThreadType, int]]:
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
                    self.client.add_view(view, message_id=message.id)
            threads_ids.append((thread_type, thread.id))
        return threads_ids

    async def clear_room_from_messages(self, guild: discord.Guild, *, include_bot: bool = False) -> None:
        room = Utils.get_music_room(guild)
        if not room:
            return

        try:
            async for message in room.history():
                if len(message.embeds) > 0 and message.author == self.client.user:
                    break
                if message.author != self.client.user or include_bot:
                    await message.delete()
        except discord.Forbidden as e:
            logger.error("No permissions: ", e)
        except discord.HTTPException as e:
            logger.error("HTTP Error: ", e)

    async def clear_room_from_reactions(self, guild: discord.Guild):
        room = Utils.get_music_room(guild)
        if not room:
            return

        try:
            async for message in room.history(oldest_first=True):
                await message.clear_reactions()
        except discord.Forbidden as e:
            logger.error("No permissions: ", e)
        except discord.HTTPException as e:
            logger.error("HTTP Error: ", e)

    ############################## Commands #################################

    @bridge.bridge_command(name="delete-music-room", aliases=["delete_room", "delete_music_room"], enabled=False)
    @commands.check_any(commands.is_owner(), commands.has_guild_permissions(administrator=True))  # type: ignore
    async def delete(self, ctx: bridge.BridgeApplicationContext) -> None:
        if music_room := Utils.get_music_room(ctx.guild):
            await music_room.delete()
            await ctx.respond(content="Music room is deleted", ephemeral=True, delete_after=5)
        await ctx.respond(content="No music room to delete", ephemeral=True, delete_after=5)

    @bridge.bridge_command(
        name="create-music-room",
        aliases=["create", "make_room", "create_room", "make_music_room", "create_music_room"],
        enabled=False,
    )
    @commands.check_any(commands.is_owner(), commands.has_guild_permissions(administrator=True))  # type: ignore
    async def create_music_room_command(self, ctx: bridge.BridgeApplicationContext) -> None:
        room_info = await self.create_music_room(ctx.guild)
        DataBase().update_room_info(room_info)
        await ctx.respond(content="New music room is created", ephemeral=True, delete_after=5)

    ############################## Listeners #################################

    @commands.Cog.listener("on_guild_join")
    async def on_guild_join(self, guild: discord.Guild):
        await self.update_music_rooms_db()

    @commands.Cog.listener("on_guild_remove")
    async def on_guild_remove(self, guild: discord.Guild):
        DataBase().music_rooms_collection.delete_one({"guild_id": guild.id})

    @commands.Cog.listener("on_message")
    async def play_music_on_message(self, message: discord.Message):
        if message.author != self.client.user and message.guild:
            prefix: str = get_config().get("PREFIX", "")

            if message.channel == Utils.get_music_room(message.guild) and not message.content.startswith(
                prefix, 0, len(prefix)
            ):
                ctx: bridge.BridgeExtContext = await self.client.get_context(message)
                try:
                    await self.invoke_command(ctx, "play", query=message.clean_content)
                except Exception as e:
                    print(e)
            await self.clear_room_from_messages(message.guild)

    @commands.Cog.listener("on_raw_reaction_add")
    async def clear_reactions_on_reaction_add(self, raw_reaction: discord.RawReactionActionEvent):
        if not raw_reaction.member:
            return

        channel = raw_reaction.member.guild.get_channel(raw_reaction.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        message = await channel.fetch_message(raw_reaction.message_id)
        if message.channel == Utils.get_music_room(message.guild):
            await message.clear_reactions()

    @commands.Cog.listener("on_ready")
    async def check_music_rooms_in_guilds_on_ready(self):
        await self.update_music_rooms_db()
        for guild in self.client.guilds:
            try:
                await self.clear_room_from_messages(guild, include_bot=True)
                await self.clear_room_from_reactions(guild)
                handler = await PlayerMessageHandler.from_room(Utils.get_music_room(guild))
                await handler.update_main_view()
                await handler.update_playing_track_embed(guild)
                await Handlers.update_threads_views(guild)
            except Exception as e:
                logger.error(f"{e}")
        await self.client.when_ready()


def setup(client: TenB_Bot):
    Handlers.setup(client)
    client.add_cog(MusicRoomCog())
