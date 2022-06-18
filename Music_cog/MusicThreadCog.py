import discord
from discord import ui
from discord.ext import bridge, commands, tasks  # type: ignore
from loguru import logger  # type: ignore

from abcs import MusicCogABC
from enums import ThreadType

from . import Utils  # type: ignore


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
                thread = Utils.get_thread(message.guild, thread_type)  # type: ignore
                if message.channel == thread:
                    try:
                        await thread.purge(check=lambda m: m.author != self.client.user)  # type: ignore
                    except Exception:
                        logger.error("Deleting messages error")

def setup(client: bridge.Bot):
    client.add_cog(MusicThreadCog(client))