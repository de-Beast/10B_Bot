import discord
from config import get_config
from discord.ext import bridge, commands
from discord.ext.pages import Page, Paginator
from Exceptions import NotInVoiceError, WrongVoiceError
from loguru import logger


class TenB_Bot(bridge.Bot):
    def __init__(self):
        super().__init__(command_prefix=get_config().get("PREFIX"), intents=discord.Intents.all())
        # Init Music modules
        from ABC import CogABC
        CogABC._client = self

        from Music_cog import setup_audio_cogs
        setup_audio_cogs(self)

        from Audio_cog import setup_audio_cogs
        setup_audio_cogs(self)

    async def when_ready(self):
        logger.info("Guild list::{guilds}", guilds=[str(guild) for guild in self.guilds])
        logger.success("Bot is ready")

    async def on_command_error(
        self,
        ctx: bridge.BridgeExtContext | bridge.BridgeApplicationContext,  # type: ignore
        error: commands.CommandError,
    ) -> None:
        if isinstance(error, NotInVoiceError):
            await ctx.respond(content=error.args[0], ephemeral=True, delete_after=5)
        elif isinstance(error, WrongVoiceError):
            await ctx.respond(content=error.args[0], ephemeral=True, delete_after=5)

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
