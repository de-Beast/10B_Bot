from discord import Permissions, User, VoiceState
from discord.ext import bridge, commands

import Music_cog.player.Player as plr
from enums import ThreadType
from Exceptions import NotInVoiceError, WrongTextChannelError, WrongVoiceError
from Music_cog import Utils


def is_connected(user_bot_same_voice: bool = True):
    async def predicate(ctx: bridge.BridgeExtContext | bridge.BridgeApplicationContext) -> bool:
        if isinstance(ctx.author, User):
            return False

        if not (condition := isinstance(ctx.author.voice, VoiceState)):
            raise NotInVoiceError("You are not in voice channel")

        condition = (
            condition
            and (
                isinstance(ctx.voice_client, plr.MusicPlayer)
                and ctx.author.voice.channel == ctx.voice_client.channel
                or ctx.voice_client is None
            )
            or not user_bot_same_voice
        )
        if not condition:
            raise WrongVoiceError("You are not in the same voice channel as Bot")

        return condition

    return commands.check(predicate)  # type: ignore


def permissions_for_play():
    async def predicate(ctx: commands.Context) -> bool:
        """Check if bot has permissions to play in user's voice channel."""
        perms: Permissions = ctx.author.voice.channel.permissions_for(ctx.me)
        condition: bool = perms.connect and perms.speak
        if not condition:
            raise commands.BotMissingPermissions(["connect", "speak"])

        return condition

    return commands.check(predicate)


def is_history_thread():
    async def predicate(ctx: bridge.BridgeExtContext | bridge.BridgeApplicationContext) -> bool:
        condition = ctx.channel == Utils.get_thread(ctx.guild, ThreadType.HISTORY)
        if not condition:
            raise WrongTextChannelError("Called not from History thread")
        return condition

    return commands.check(predicate)
