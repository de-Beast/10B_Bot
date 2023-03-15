import re

import discord
from ABC import MusicCogABC
from discord.ext import bridge, commands
from enums import SearchPlatform, ThreadType
from loguru import logger

from . import Utils
from .room.Handlers import (
    HistoryThreadHandler,
    QueueThreadHandler,
    SettingsThreadHandler,
)
from .Utils import is_connected


def is_history_thread():
    def predicate(ctx: bridge.BridgeExtContext | bridge.BridgeApplicationContext) -> bool:
        return ctx.channel == Utils.get_thread(ctx.guild, ThreadType.HISTORY)

    return commands.check(predicate)


class MusicThreadCog(MusicCogABC):
    async def clear_room_from_reactions(self, guild: discord.Guild):
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

    @commands.message_command(name="Add Track From History")
    @is_history_thread()
    @is_connected(False)
    async def add_track_from_history(self, ctx: discord.ApplicationContext, message: discord.Message):
        await ctx.defer(ephemeral=True, invisible=False)
        embed = message.embeds[0]
        new_ctx = await self.client.get_context(message)
        new_ctx.author = ctx.author
        search_platform: SearchPlatform | None = None
        if isinstance(embed.description, str):
            for search_plat in SearchPlatform:
                if match := re.search(search_plat.value, embed.description):
                    search_platform = SearchPlatform.get_key(match[0])
                    break
        setattr(new_ctx, "search_platform", search_platform)
        await self.invoke_command(new_ctx, "play", query=embed.title)
        await ctx.send_followup(content="Success", delete_after=3)

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
    async def clear_threads_on_ready(self):
        for guild in self.client.guilds:
            try:
                handler = QueueThreadHandler(Utils.get_thread(guild, ThreadType.QUEUE))
                await handler.thread.purge(limit=None)

                handler = SettingsThreadHandler(Utils.get_thread(guild, ThreadType.SETTINGS))
                await handler.thread.purge(limit=None, check=lambda m: m.author != self.client.user)

                handler = HistoryThreadHandler(Utils.get_thread(guild, ThreadType.SETTINGS))
                await handler.thread.purge(limit=None, check=lambda m: m.author != self.client.user)
            except Exception as e:
                logger.error(f"{e}")
            finally:
                await self.clear_room_from_reactions(guild)

    @commands.Cog.listener("on_raw_reaction_add")
    async def clear_reactions_on_reaction_add(self, raw_reaction: discord.RawReactionActionEvent):
        if not raw_reaction.member:
            return

        thread = raw_reaction.member.guild.get_thread(raw_reaction.channel_id)
        if not isinstance(thread, discord.Thread):
            return

        if thread.parent == Utils.get_music_room(thread.guild):
            message: discord.Message = await thread.fetch_message(raw_reaction.message_id)
            await message.clear_reactions()


def setup(client: bridge.Bot):
    client.add_cog(MusicThreadCog(client))
