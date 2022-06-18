import discord
from discord.ext import bridge, commands  # type: ignore
from discord.ext.pages import Page, Paginator  # type: ignore
from loguru import logger

import Music_cog
from config import settings


class TenB_Bot(bridge.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=settings["prefix"], intents=discord.Intents.all()
        )
        # Init Music modules
        Music_cog.setup_music_cogs(self)

    async def when_ready(self):
        logger.info("Guild list::{guilds}", guilds = [str(guild) for guild in self.guilds])
        logger.success("Bot is ready")

    @commands.command(name="test")
    async def test(self, ctx: commands.Context):
        my_pages = [
            Page(
                content="This is my first page. It has a list of embeds and message content.",
                embeds=[
                    discord.Embed(title="My First Embed Title"),
                    discord.Embed(title="My Second Embed Title"),
                ],
            ),
            Page(
                content="This is my second page. It only has message content.",
            ),
            Page(
                embeds=[
                    discord.Embed(
                        title="This is my third page.",
                        description="It has no message content, and one embed.",
                    )
                ],
            ),
        ]
        paginator = Paginator(pages=my_pages)
        await paginator.send(ctx)
