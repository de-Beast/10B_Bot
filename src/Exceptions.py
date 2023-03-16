from discord.ext import commands


class WrongVoiceError(commands.CommandError):
    ...


class NotInVoiceError(WrongVoiceError):
    ...


class WrongTextChannelError(commands.CommandError):
    ...
