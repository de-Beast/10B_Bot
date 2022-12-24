from ..abcs import MusicCogABC
from typing import Any

import discord
from discord.ext import bridge, commands, tasks
from loguru import logger

from config import get_config
from ..MongoDB import DataBase

from . import MusicRoom_utils as mrUtils
from . import Utils
from .player import MusicPlayer
from .room import Handlers
from .room.Handlers import MainMessageHandler, ThreadHandler


class MusicRoomCog(MusicCogABC):
    @tasks.loop(seconds=1)
    async def display_playing_track(
        self, room: discord.TextChannel, player: MusicPlayer
    ):
        try:
            track = player.track
        except Exception:
            track = None
        if self.display_playing_track.__getattribute__("track") != track:
            self.display_playing_track.__setattr__("track", track)
            handler = await MainMessageHandler.with_message_from_room(room)
            if handler:
                await handler.update_embed(
                    room.guild, track, player.shuffle if track is not None else None
                )

    async def clear_room(self, guild: discord.Guild):
        room = Utils.get_music_room(guild)
        try:
            while len(await room.history(oldest_first=True).flatten()) > 3:  # type: ignore
                try:
                    await room.purge(check=lambda m: m.author != self.client.user)  # type: ignore
                except Exception:
                    logger.error("Deleting messages error")
        except Exception:
            logger.error("Unknown Channel")

    ############################## Commands #################################

    @commands.command(name="delete")
    async def delete(self, ctx: commands.Context):
        await ctx.channel.delete()

    @commands.command(
        name="create_music_room",
        aliases=["create", "make_room", "create_room", "make_music_room"],
    )
    @commands.check_any(
        commands.is_owner(), commands.has_guild_permissions(administrator=True)  # type: ignore
    )
    async def command_create_music_room(self, ctx: commands.Context):
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
        if message.author != self.client.user:
            if message.channel == Utils.get_music_room(
                message.guild
            ) and not message.content.startswith(
                get_config().get("PREFIX", ""), 0, len(get_config().get("PREFIX", ""))
            ):
                ctx: bridge.BridgeExtContext = await self.client.get_context(message)
                ctx.args = [message.content]
                await self.invoke_command(ctx, "play")
                await self.clear_room(ctx.guild)

    @commands.Cog.listener("on_ready")
    async def check_music_rooms_in_guilds(self):
        await mrUtils.update_music_rooms_db(self.client)
        for guild in self.client.guilds:
            try:
                handler = await MainMessageHandler.with_message_from_room(
                    Utils.get_music_room(guild)
                )
                handler.update_main_view()
                await handler.update_embed(guild)
                await ThreadHandler.update_threads_views(guild)
            except Exception as e:
                logger.error(f"{e}")
        await self.client.when_ready()

    @commands.Cog.listener("on_voice_state_update")
    async def binding_playing_track_view(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if (
            self.client.user
            and member.id == self.client.user.id
            and before.channel != after.channel
        ):
            if after.channel is not None:
                try:
                    player: MusicPlayer | Any = member.guild.voice_client
                    if not isinstance(player, MusicPlayer):
                        raise Exception("Not a Player Class")
                except Exception as e:
                    logger.error(e)
                if not self.display_playing_track.is_running():
                    self.display_playing_track.__setattr__("track", None)
                    self.display_playing_track.start(
                        Utils.get_music_room(member.guild), player
                    )
            else:
                self.display_playing_track.cancel()
                handler = await MainMessageHandler.with_message_from_room(
                    Utils.get_music_room(member.guild)
                )
                if handler:
                    await handler.update_embed(member.guild)


def setup(client: bridge.Bot):
    Handlers.setup(client)
    client.add_cog(MusicRoomCog(client))
