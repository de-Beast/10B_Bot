from enum import Enum
from time import sleep

import discord
from discord.ext import commands

from .Track import Track

Loop = Enum("Loop", "NOLOOP LOOP ONE", start=0)


class Player(discord.VoiceClient):
    # TODO: Сделать работу с плейлистами (вроде изи)
    def __init__(self, client: commands.Bot, channel: discord.TextChannel):
        super().__init__(client, channel)

        self.queue = []
        self.looping = Loop.NOLOOP
        self.is_secret_shaffling = False

    def has_track(self):
        return self.is_playing() or self.is_paused()

    def play_next(self):
        if len(self.queue) > 0:
            track: Track = self.queue[0]
            self.play(track.src, after=lambda a: self.update_queue())
            self.pause()
            sleep(1)
            self.resume()

    def update_queue(self):
        if self.looping == Loop.NOLOOP:
            self.queue.pop(0)

        elif self.looping == Loop.LOOP:
            self.queue[0]
            self.queue.pop(0)

        elif self.looping == Loop.ONE:
            self.stop()

        self.play_next()

    def set_loop(self, loop_type: Loop):
        self.looping = loop_type

    def stop(self):
        self.queue.clear()
        super().stop()

    def toggle(self):
        if self.is_playing():
            self.pause()
        elif self.is_paused():
            self.resume()

    def skip(self):
        if self.is_playing():
            super().stop()
            # self.player.pause()
        # self.update_queue()

    async def add_tracks_to_queue(self, tracks_all_meta: list):
        for track_all_meta in tracks_all_meta:
            if not track_all_meta:
                continue
            track = None
            track = await Track.from_dict(track_all_meta)
            if track:
                self.queue.append(track)
                for track in self.queue:
                    print(track.title, end="\t")
                print()
            if not self.has_track():
                self.play_next()
            sleep(0.75)
