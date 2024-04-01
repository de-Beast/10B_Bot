import asyncio
import datetime

import discord
from discord.ext import bridge, commands
from loguru import logger

import Checks
from ABC import CogABC
from enums import SearchPlatform, ThreadType
from Exceptions import NotInVoiceError, WrongVoiceError
from Music_cog.player.Track import MetaData

from . import Utils
from .player import MusicPlayer
from .room.Handlers import SettingsThreadHandler


class MusicPlayerCog(CogABC):
    ############################## Commands #################################

    # GROUP - PLAY
    @bridge.bridge_command(
        name="play",
        aliases=["p", "add", "paly"],
        description="Finds track (or video) by query depending on the search platform and adds it to the queue",
        description_localizations={
            "ru": "Находит трек (видео) по запросу, исходя из выбранной платформы поиска, и добавляет его в очередь",
        },
        enabled=False,
    )
    @Checks.permissions_for_play()
    @Checks.is_connected(user_bot_same_voice=False)
    @commands.cooldown(1, 5, commands.BucketType.default)
    @discord.option("query", str, description="Query to search")
    # async def play(self, ctx: bridge.BridgeExtContext | bridge.BridgeApplicationContext, *, query: str):
    async def play(self, ctx: bridge.BridgeApplicationContext, *, query: str):
        await ctx.defer(ephemeral=True)
        if not isinstance(player := ctx.voice_client, MusicPlayer):
            return

        if (
            player
            and player.has_track
            and isinstance(ctx, bridge.BridgeExtContext)
            and not query
        ):
            await self.invoke_command(ctx, "pause_resume")
            return
        if not query:
            return

        search_platform: SearchPlatform = getattr(
            ctx,
            "search_platform",
            (
                await SettingsThreadHandler(thread).get_search_platform()
                if (thread := Utils.get_thread(ctx.guild, ThreadType.SETTINGS))
                else SearchPlatform.YOUTUBE
            ),
        )
        request_data = MetaData(
            {
                "title": "",
                "author": "",
                "thumbnail": "",
                "platform": search_platform,
                "requested_by": ctx.author,
                "requested_at": datetime.datetime.now(tz=datetime.timezone.utc),
            }
        )
        await player.add_query(query, request_data)
        if ctx.is_app:
            await ctx.respond(
                content="Track is successfully added", ephemeral=True, delete_after=5
            )

    @play.before_invoke
    async def connection_to_voice_channel(
        self, ctx: bridge.BridgeApplicationContext
    ) -> None:
        if isinstance(ctx.author, discord.User) or ctx.author is None:
            return
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            return
        if ctx.voice_client is None:
            await ctx.author.voice.channel.connect(
                cls=lambda client, connectable: MusicPlayer(client, connectable),  # type: ignore
                reconnect=True,
            )
        elif ctx.author.voice.channel != ctx.voice_client.channel:
            most_authoritative_role: discord.Role | None = None
            if isinstance(ctx.voice_client, MusicPlayer) and isinstance(
                ctx.voice_client.channel, (discord.VoiceChannel, discord.StageChannel)
            ):
                for member in ctx.voice_client.channel.members:
                    if (
                        most_authoritative_role is None
                        or most_authoritative_role > member.top_role
                    ):
                        most_authoritative_role = member.top_role
                if (
                    most_authoritative_role is not None
                    and most_authoritative_role <= ctx.author.top_role
                ):
                    await ctx.voice_client.move_to(ctx.author.voice.channel)
                else:
                    raise WrongVoiceError

    @play.error
    async def play_command_error(
        self, ctx: bridge.BridgeApplicationContext, error: commands.CommandError
    ) -> None:
        if isinstance(error, NotInVoiceError):
            if isinstance(ctx.voice_client, MusicPlayer) and ctx.voice_client.has_track:
                message = f"The Bot is currently playing music, try to join {ctx.me.voice.channel.mention}"
                await ctx.respond(content=message, ephemeral=True, delete_after=5)
            else:
                message = "You are not in the voice channel, command will be reinvoked after this message is being deleted"
                await ctx.respond(content=message, ephemeral=True, delete_after=5)
                try:
                    await self.client.wait_for(
                        "voice_state_update",
                        check=lambda member, before, after: (
                            member == ctx.author and after.channel is not None
                        ),
                        timeout=5,
                    )
                except asyncio.TimeoutError:
                    return
                else:
                    if (
                        isinstance(ctx, bridge.BridgeApplicationContext)
                        and isinstance(ctx.command, bridge.BridgeSlashCommand)
                        and ctx.selected_options
                    ):
                        await self.invoke_command(
                            ctx, "play", query=ctx.selected_options[0]["value"]
                        )
                    elif isinstance(ctx, bridge.BridgeExtContext):
                        await self.invoke_command(
                            ctx, "play", query=ctx.message.clean_content
                        )
        elif isinstance(error, commands.BotMissingPermissions):
            message = f"Bot is missing {' and '.join(error.missing_permissions)} permissions to join the voice channel"
            await ctx.respond(content=message, ephemeral=True, delete_after=5)
        elif isinstance(error, WrongVoiceError):
            message = "You can't move bot to your channel because someone in bot's channel has higher role than yours"
            await ctx.respond(content=message, ephemeral=True, delete_after=5)

    @bridge.bridge_command(
        name="disconnect", aliases=["dis", "d", "leave"], enabled=False
    )
    @Checks.is_connected()
    async def disconnect(self, ctx: bridge.BridgeApplicationContext):
        if isinstance(ctx.voice_client, MusicPlayer):
            await ctx.voice_client.disconnect()
            await ctx.respond(content="Disconnected", ephemeral=True, delete_after=5)

    ############################## Listeners ################################

    @commands.Cog.listener("on_command_error")
    async def on_command_error(
        self, ctx: bridge.BridgeApplicationContext, error: commands.CommandError
    ):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.respond("You are missing some arguments", delete_after=5)
        elif isinstance(error, commands.BadArgument):
            await ctx.respond("You are using bad arguments", delete_after=5)
        elif isinstance(error, commands.CheckFailure):
            await ctx.respond("You are not in the voice channel", delete_after=5)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.respond("You are on cooldown", delete_after=5)
        elif isinstance(error, commands.DisabledCommand):
            await ctx.respond("Please, use slash command", delete_after=5)
        else:
            logger.opt(exception=error).error("bruh")
            await ctx.respond(
                f"Bruh... Something went wrong -> {error}", delete_after=5
            )


def setup(client: bridge.Bot):
    client.add_cog(MusicPlayerCog())
