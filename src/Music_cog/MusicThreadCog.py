import discord
from discord.ext import bridge, commands
from loguru import logger

from src.abcs import MusicCogABC
from src.enums import ThreadType

from . import Utils
from .room import Handlers
from .room.Handlers import QueueThreadHandler, SettingsThreadHandler


class MusicThreadCog(MusicCogABC):
    ############################ Commands ###############################

    # @commands.slash_command(name="swap")
    # async def swap_tracks(self, ctx: discord.ApplicationContext,
    #                       track: discord.Option(input_type=str|int, )):
    #     pass

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
            except Exception as e:
                logger.error(f"{e}")


def setup(client: bridge.Bot):
    client.add_cog(MusicThreadCog(client))
