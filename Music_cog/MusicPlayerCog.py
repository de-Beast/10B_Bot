import asyncio
from typing import Optional

import discord
from discord.ext import bridge, commands  # type: ignore
from loguru import logger

from abcs import MusicCogABC
from enums import Loop, SearchPlatform, ThreadType

from . import Utils
from .player import Player
from .room.Handlers import MainMessageHandler, ThreadsHandler  # type: ignore


async def join(ctx: bridge.BridgeContext) -> bool:
    if ctx.author.voice is None:
        await ctx.send("You are not in the voice channel", delete_after=3)
        return False
    await ctx.author.voice.channel.connect(reconnect=True, cls=Player)
    return True


############################## Checks ###################################


def is_connected():  # TODO  Проверка на подключение к каналу (для Play использовать error handler)
    def predicate(ctx: bridge.BridgeContext) -> bool:
        return (
            isinstance(ctx.voice_client, Player)
            and ctx.author.voice is not None
            and ctx.author.voice.channel == ctx.voice_client.channel
        )

    return commands.check(predicate)


class MusicPlayerCog(MusicCogABC):

    ############################## Commands #################################

    # GROUP - PLAY
    @bridge.bridge_command(name="play", aliases=["p", "add", "paly"], enabled=False)
    @commands.cooldown(1, 5, commands.BucketType.default)
    # @is_connected()
    async def play(self, ctx: bridge.BridgeContext, *, query: str):
        try:
            await ctx.defer()
        except Exception:
            pass
        if await self.connection_to_voice_channel(ctx):
            player: Player = ctx.voice_client  # type: ignore
            if player.has_track and not query:
                await self.invoke_command(ctx, "pause_resume")
                return
            if not query:
                return
            if (thread := Utils.get_thread(ctx.guild, ThreadType.SETTINGS)) is not None:
                search_platform: SearchPlatform = await ThreadsHandler.SettingsThreadHandler(
                    thread
                ).search_platform
            await player.add_query(query, search_platform, ctx.message)
        try:
            await ctx.delete()
        except discord.NotFound:
            pass
        # tracks_all_meta = mp.define_stream_method(
        #     music_name, search_platform=self.search_platform
        # )
        # # if list(tracks_all_meta) == [None]:
        # # 	await ctx.send('Bruh... Something went wrong')
        # # 	return None
        # Thread(
        #     target=asyncio.run, args=[player.add_tracks_to_queue(tracks_all_meta)]
        # ).start()

    # @play.before_invoke
    async def connection_to_voice_channel(self, ctx: bridge.BridgeContext) -> bool:
        try:
            if ctx.author.voice is None:
                if ctx.voice_client.has_track:
                    message = "The Bot is currently playing music, try to join this voice channel"
                    await ctx.respond(message, delete_after=5)
                else:
                    message = "You are not in the voice channel, command will be reinvoked after this message is being deleted"
                    await ctx.respond(message, delete_after=5)
                    try:
                        await self.client.wait_for(
                            "voice_state_update",
                            check=lambda member, before, after: (
                                member == ctx.author and after.channel is not None
                            ),
                            timeout=5,
                        )
                    except asyncio.TimeoutError:
                        pass
                    else:
                        await ctx.invoke(
                            ctx.command, *(opt["value"] for opt in ctx.selected_options)
                        )
                    return False
            elif ctx.voice_client is None:
                player = await ctx.author.voice.channel.connect(reconnect=True, cls=Player)
                handler = await MainMessageHandler.with_message(Utils.get_music_room(ctx.guild))
                player.set_settings(handler.looping, handler.shuffle)
            elif ctx.author.voice.channel != ctx.voice_client.channel:
                most_authoritative_role: Optional[discord.Role] = None
                for member in ctx.voice_client.channel.members:
                    if (
                        most_authoritative_role is None
                        or most_authoritative_role > member.top_role
                    ):
                        most_authoritative_role = member.top_role
                if most_authoritative_role <= ctx.author.top_role:
                    await ctx.voice_client.disconnect()
                    await asyncio.sleep(1)
                    player = await ctx.author.voice.channel.connect(reconnect=True, cls=Player)
                    handler = await MainMessageHandler.with_message(Utils.get_music_room(ctx.guild))
                    player.set_settings(handler.looping, handler.shuffle)
                else:
                    message = "The member with more authoritative role is currently using the bot"
                    await ctx.respond(message, delete_after=5)
                    return False
        except (commands.BotMissingPermissions, commands.BotMissingAnyRole):
            message = "Bot is missing permissions to join the voice channel"
            ctx.respond(message, delete_after=5)
        except discord.HTTPException:
            pass
        else:
            return True
        return False

    @bridge.bridge_command(
        name="pause_resume",
        aliases=["pause", "pa", "pas", "resume", "res", "re", "toggle", "tog"],
    )
    @is_connected()
    async def pause_resume(self, ctx: bridge.BridgeContext):
        ctx.voice_client.toggle()

    @bridge.bridge_command(name="skip", aliases=["s", "next"])
    @is_connected()
    async def skip(self, ctx: bridge.BridgeContext):
        ctx.voice_client.skip()

    @bridge.bridge_command(name="stop")
    @is_connected()
    async def stop(self, ctx: bridge.BridgeContext):
        ctx.voice_client.stop()

    @commands.group(name="loop", aliases=["l"])
    @is_connected()
    async def loop(self, ctx: bridge.BridgeContext):
        player = ctx.voice_client
        if player.looping == Loop.LOOP:
            player.looping = Loop.NOLOOP
        else:
            player.looping = Loop.LOOP

    @loop.command(name="one", aliases=["1"])
    async def loop_one(self, ctx: bridge.BridgeContext):
        ctx.voice_client.looping = Loop.ONE

    @loop.command(name="none", aliases=["n", "no", "nothing"])
    async def no_loop(self, ctx: bridge.BridgeContext):
        ctx.voice_client.looping = Loop.NOLOOP

    @commands.command(name="disconnect", aliases=["dis", "d", "leave"])
    @is_connected()
    async def disconnect(self, ctx: bridge.BridgeContext):
        await ctx.voice_client.disconnect()

        ############################# Listeners #############################

    @commands.Cog.listener("on_command_error")
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
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
            if ctx.command.name == "play":
                await ctx.send(
                    "Please, use slash command or just type your query", delete_after=3
                )
        else:
            logger.opt(exception=error).error("bruh")
            await ctx.send(f"Bruh... Something went wrong -> {error}", delete_after=3)


def setup(client: bridge.Bot):
    client.add_cog(MusicPlayerCog(client))
