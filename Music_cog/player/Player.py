from enum import Enum
from time import sleep

import discord
from discord.ext import commands

Loop = Enum('Loop', 'NOLOOP LOOP ONE', start = 0)

class Player(discord.VoiceClient):
    # TODO: Сделать работу с плейлистами (вроде изи)
    def __init__(self, client: commands.Bot, channel: discord.TextChannel):
        super().__init__(client, channel)

        self.FFMPEG_OPTIONS = {
			'before_options': ' \
				-reconnect 1 \
				-reconnect_streamed 1 \
				-reconnect_at_eof 1 \
				-reconnect_on_network_error 1 \
				-reconnect_on_http_error 1 \
				-reconnect_delay_max 2',
			'options': '-vn'
		}

        self.queue = []
        self.looping = Loop.NOLOOP
        self.is_secret_shaffling = False


    def has_track(self):
        return self.is_playing() or self.is_paused()


    def play_next(self):
        if len(self.queue) > 0:
            track = self.queue[0]['source']
            self.play(track, after = lambda a: self.update_queue())
            self.pause()
            sleep(1)
            self.resume()


    def update_queue(self):
        if self.looping == Loop.NOLOOP:
            self.queue.pop(0)
        elif self.looping == Loop.LOOP:
            self.queue[0]['source'].cleanup()
            self.queue.append(self.queue[0])
            self.queue.pop(0)
        elif self.looping == Loop.ONE:
            self.stop()
            self.queue[0]['source'].cleanup()
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


    async def add_tracks_to_queue(self, ctx, tracks_all_meta: list):
        for track_all_meta in tracks_all_meta:
            if not track_all_meta:
                continue
            source = await discord.FFmpegOpusAudio.from_probe(track_all_meta['source'], **self.FFMPEG_OPTIONS)
            track = {
                'source': source,
                'meta': track_all_meta['meta']
            }
            if source:
                self.queue.append(track)
                print(*self.queue)
            if not self.has_track():
                self.play_next()
            sleep(0.75)
