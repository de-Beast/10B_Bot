import discord
from ABC import MusicCogABC
from Bot import TenB_Bot
from config import get_config
from discord.ext import bridge, commands
from loguru import logger
from MongoDB import DataBase

from . import MusicRoom_utils as mrUtils
from . import Utils
from .room import Handlers
from .room.Handlers import PlayerMessageHandler


class MusicRoomCog(MusicCogABC):
    async def clear_room_from_user_messages(self, guild: discord.Guild):
        room = Utils.get_music_room(guild)
        if not room:
            return

        try:
            while sum(map(lambda m: m.author != self.client.user, await room.history(oldest_first=True).flatten())):
                await room.purge(check=lambda m: m.author != self.client.user)
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

    @commands.command(name="delete")
    async def delete(self, ctx: commands.Context):
        await ctx.channel.delete()

    @commands.command(
        name="create_music_room",
        aliases=["create", "make_room", "create_room", "make_music_room"],
    )
    @commands.check_any(commands.is_owner(), commands.has_guild_permissions(administrator=True))  # type: ignore
    async def create_music_room_command(self, ctx: commands.Context):
        room_info = await mrUtils.create_music_room(self.client, ctx.guild)
        DataBase().update_room_info(room_info)

    ############ Listeners ############

    @commands.Cog.listener("on_guild_join")
    async def on_guild_join(self, guild: discord.Guild):
        await mrUtils.update_music_rooms_db(self.client)

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
                # if message.channel == Utils.get_music_room(message.guild):
                ctx: bridge.BridgeExtContext = await self.client.get_context(message)
                ctx.args = [message.content]
                try:
                    await self.invoke_command(ctx, "play")
                except Exception as e:
                    print(e)
            await self.clear_room_from_user_messages(message.guild)

    @commands.Cog.listener("on_raw_reaction_add")
    async def clear_reactions_on_reaction_add(self, raw_reaction: discord.RawReactionActionEvent):
        if not raw_reaction.member:
            return

        channel = raw_reaction.member.guild.get_channel(raw_reaction.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        message: discord.Message = await channel.fetch_message(raw_reaction.message_id)
        if message.channel == Utils.get_music_room(message.guild):
            await message.clear_reactions()

    @commands.Cog.listener("on_ready")
    async def check_music_rooms_in_guilds_on_ready(self):
        await mrUtils.update_music_rooms_db(self.client)
        for guild in self.client.guilds:
            try:
                await self.clear_room_from_user_messages(guild)
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
    client.add_cog(MusicRoomCog(client))
