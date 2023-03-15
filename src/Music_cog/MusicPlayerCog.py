import asyncio
import datetime

import discord
from ABC import MusicCogABC
from discord.ext import bridge, commands
from enums import SearchPlatform, ThreadType
from loguru import logger

from Music_cog.player.Track import MetaData

from . import Utils
from .player import MusicPlayer
from .room.Handlers import SettingsThreadHandler
from .Utils import is_connected

############################## Checks ###################################


class MusicPlayerCog(MusicCogABC):
    ############################## Commands #################################

    # GROUP - PLAY
    @bridge.bridge_command(
        name="play",
        aliases=["p", "add", "paly"],
        description="Finds track(or video) by query depending on the search platform and adds it to the queue",
        description_localizations={
            "ru": "Находит трек(видео) по запросу, исходя из выбранной платформы поиска, и добавляет его в очередь",
        },
        enabled=False,
    )
    @commands.cooldown(1, 5, commands.BucketType.default)
    async def play(
        self,
        ctx: bridge.BridgeExtContext | bridge.BridgeApplicationContext,
        *,
        query: str,
    ):
        try:
            await ctx.defer(ephemeral=True, invisible=False)
        except Exception:
            pass
        if not isinstance(player := ctx.voice_client, MusicPlayer):
            return

        if player and player.has_track and isinstance(ctx, bridge.BridgeExtContext) and not query:
            await self.invoke_command(ctx, "pause_resume")
            return
        if not query:
            return

        search_platform: SearchPlatform = getattr(
            ctx,
            "search_platform",
            await SettingsThreadHandler(thread).search_platform
            if (thread := Utils.get_thread(ctx.guild, ThreadType.SETTINGS))
            else SearchPlatform.YOUTUBE,
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
        await ctx.respond(content="Success", delete_after=3)
        

    @play.before_invoke
    async def connection_to_voice_channel(self, ctx: bridge.BridgeExtContext | bridge.BridgeApplicationContext) -> None:
        try:
            if ctx.author.voice is None:
                if isinstance(ctx.voice_client, MusicPlayer) and ctx.voice_client.has_track:
                    message = "The Bot is currently playing music, try to join this voice channel"
                    await ctx.respond(message, delete_after=5)
                else:
                    message = "You are not in the voice channel, command will be reinvoked after this message is being deleted"
                    await ctx.respond(message, delete_after=5)
                    try:
                        await self.client.wait_for(
                            "voice_state_update",
                            check=lambda member, before, after: (member == ctx.author and after.channel is not None),
                            timeout=5,
                        )
                    except asyncio.TimeoutError:
                        pass
                    else:
                        if ctx.is_app and isinstance(ctx.command, bridge.BridgeCommand):
                            await ctx.invoke(
                                ctx.command.slash_variant,
                                *(opt["value"] for opt in ctx.selected_options),
                            )
                    return
            elif ctx.voice_client is None:
                player = await ctx.author.voice.channel.connect(reconnect=True, cls=MusicPlayer)
                await player.init()
            elif ctx.author.voice.channel != ctx.voice_client.channel:
                most_authoritative_role: discord.Role | None = None
                if isinstance(ctx.voice_client, MusicPlayer) and isinstance(
                    ctx.voice_client.channel,
                    (discord.VoiceChannel, discord.StageChannel),
                ):
                    for member in ctx.voice_client.channel.members:
                        if most_authoritative_role is None or most_authoritative_role > member.top_role:
                            most_authoritative_role = member.top_role
                    if most_authoritative_role <= ctx.author.top_role:
                        await ctx.voice_client.disconnect()
                        await asyncio.sleep(1)
                        player = await ctx.author.voice.channel.connect(reconnect=True, cls=MusicPlayer)
                        await player.init()
                    else:
                        await ctx.respond(message, delete_after=5)
                        return
        except (commands.BotMissingPermissions, commands.BotMissingAnyRole):
            message = "Bot is missing permissions to join the voice channel"
            await ctx.respond(message, delete_after=5)
        except discord.HTTPException as e:
            await ctx.send(f"Bruh... Something went wrong -> {e}", delete_after=5)

    @bridge.bridge_command(name="disconnect", aliases=["dis", "d", "leave"])
    @is_connected()
    async def disconnect(self, ctx: bridge.BridgeExtContext | bridge.BridgeApplicationContext):
        if isinstance(ctx.voice_client, MusicPlayer):
            await ctx.voice_client.disconnect()

        ############################# Listeners #############################

    @commands.Cog.listener("on_command_error")
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You are missing some arguments", delete_after=3)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("You are using bad arguments", delete_after=3)
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("You are not in the voice channel", delete_after=3)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send("You are on cooldown", delete_after=3)
        elif isinstance(error, commands.DisabledCommand):
            if ctx.command and ctx.command.name == "play":
                await ctx.send("Please, use slash command or just type your query", delete_after=3)
        else:
            logger.opt(exception=error).error("bruh")
            await ctx.send(f"Bruh... Something went wrong -> {error}", delete_after=3)


def setup(client: bridge.Bot):
    client.add_cog(MusicPlayerCog(client))
