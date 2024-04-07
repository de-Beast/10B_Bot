import re

import discord
from discord.ext import bridge, commands
from loguru import logger

import Checks
from ABC import CogABC
from enums import SearchPlatform, ThreadType
from Exceptions import NotInVoiceError, WrongTextChannelError

from . import Utils
from .player import MusicPlayer
from .room.Handlers import (
    HistoryThreadHandler,
    QueueThreadHandler,
    SettingsThreadHandler,
)

# TODO Команда для удаления трека из очереди


class MusicThreadCog(CogABC):
    async def clear_thread_from_reactions(self, guild: discord.Guild) -> None:
        threads = [Utils.get_thread(guild, thread_type) for thread_type in ThreadType]
        for thread in threads:
            if thread:
                try:
                    async for message in thread.history(oldest_first=True):
                        await message.clear_reactions()
                except discord.Forbidden as e:
                    logger.error("No permissions: ", e)
                except discord.HTTPException as e:
                    logger.error("HTTP Error: ", e)

    ############################ Commands ###############################

    @commands.message_command(name="add from history")
    @Checks.is_thread(ThreadType.HISTORY)
    @Checks.permissions_for_play()
    @Checks.is_connected(same_voice=False)
    async def add_track_from_history(
        self, ctx: discord.ApplicationContext, message: discord.Message
    ) -> None:
        await ctx.defer(ephemeral=True, invisible=False)
        embed = message.embeds[0]
        new_ctx = await self.client.get_context(message)
        new_ctx.author = ctx.author
        search_platform: SearchPlatform | None = None
        if isinstance(embed.description, str):
            for search_plat in SearchPlatform:
                if match := re.search(search_plat.value, embed.description):
                    search_platform = SearchPlatform.get_key(match.group(0))
                    break
        setattr(new_ctx, "search_platform", search_platform)
        await self.invoke_command(
            new_ctx,
            "play",
            query=f"{embed.title} {embed.author.name if embed.author else ''}",
        )
        await ctx.respond(
            content="Track is added from history", ephemeral=True, delete_after=5
        )

    @add_track_from_history.error
    async def add_track_from_history_error(
        self, ctx: discord.ApplicationContext, error: commands.CommandError
    ) -> None:
        if isinstance(error, WrongTextChannelError):
            await ctx.respond(content=error.args[0], ephemeral=True, delete_after=5)
        elif isinstance(error, NotInVoiceError):
            await ctx.respond(content=error.args[0], ephemeral=True, delete_after=5)
        elif isinstance(error, commands.BotMissingPermissions):
            message = f"Bot is missing {' and '.join(error.missing_permissions)} permissions to join the voice channel"
            await ctx.respond(content=message, ephemeral=True, delete_after=5)

    @commands.message_command(name="remove from queue")
    @Checks.is_thread(ThreadType.QUEUE)
    @Checks.is_connected(same_voice=True)
    async def remove_track_from_queue(self, ctx: discord.ApplicationContext, message: discord.Message) -> None:
        await ctx.defer(ephemeral=True, invisible=False)
        player = ctx.guild.voice_client
        if isinstance(player, MusicPlayer):
            await player.stop_player()
        await ctx.respond(content="Track is removed from queue", ephemeral=True, delete_after=5)
    
    ############################# Listeners #############################

    @commands.Cog.listener("on_message")
    async def delete_human_message(self, message: discord.Message):
        if message.author != self.client.user:
            for thread_type in ThreadType:
                thread = Utils.get_thread(message.guild, thread_type)
                if message.channel == thread:
                    try:
                        await thread.purge(check=lambda m: m.author != self.client.user)
                    except Exception:
                        logger.error("Deleting messages error")

    @commands.Cog.listener("on_ready")
    async def clear_threads_on_ready(self) -> None:
        for guild in self.client.guilds:
            try:
                handler: QueueThreadHandler | SettingsThreadHandler | HistoryThreadHandler | None
                
                if handler := QueueThreadHandler.from_guild(guild):
                    await handler.thread.purge(limit=None)

                if handler := SettingsThreadHandler.from_guild(guild):
                    await handler.thread.purge(
                        limit=None, check=lambda m: m.author != self.client.user
                    )

                if handler := HistoryThreadHandler.from_guild(guild):
                    await handler.thread.purge(
                        limit=None, check=lambda m: m.author != self.client.user
                    )
            except Exception as e:
                logger.error(f"{e}")
            finally:
                await self.clear_thread_from_reactions(guild)

    @commands.Cog.listener("on_raw_reaction_add")
    async def clear_reactions_on_reaction_add(
        self, raw_reaction: discord.RawReactionActionEvent
    ):
        if not raw_reaction.member:
            return

        thread = raw_reaction.member.guild.get_thread(raw_reaction.channel_id)
        if not isinstance(thread, discord.Thread):
            return

        if thread.parent == Utils.get_music_room(thread.guild):
            message: discord.Message = await thread.fetch_message(
                raw_reaction.message_id
            )
            await message.clear_reactions()


def setup(client: bridge.Bot):
    client.add_cog(MusicThreadCog())
