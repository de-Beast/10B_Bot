import asyncio
from threading import Thread

import discord

from .MusicRoomCog import display_playing_track
from .player.Track import Track


class PlayerRoomBridge:
    def __init__(self, guild: discord.Guild, track: Track):
        self.guild = guild
        self.track = track

    def get_track(self) -> Track:
        return self.track

    def get_guild(self) -> discord.Guild:
        return self.guild

    def set_track(self, track: Track):
        self.track = track

    def set_guild(self, guild: discord.Guild):
        self.guild = guild


def create_bridge(guild: discord.Guild, track: Track):
    bridge = PlayerRoomBridge(guild, track)
    Thread(target=asyncio.run, args=[display_playing_track(bridge)]).start()
