import asyncio
import re

import discord
import speech_recognition as sr  # type: ignore
from discord.ext import bridge, commands

import ABC


class SpeechToTextCog(ABC.CogABC):
    def compare_speech_to_text(self, rec: sr.Recognizer, audio: sr.AudioData):
        text = rec.recognize_google(audio, language="ru")
        if match := re.search("я не какал", text, re.IGNORECASE):
            print(match.group(1))

    async def listen_users(self, vc: discord.VoiceClient) -> None:
        rec = sr.Recognizer()
        sink = discord.sinks.WaveSink()
        vc.start_recording(sink, None)
        await asyncio.sleep(5)
        for audio in sink.get_all_audio():
            audio.seek(0, 0)
            rec.listen_in_background(sr.AudioFile(audio), self.compare_speech_to_text, 1)

    async def stop_user_listening(self, vc: discord.VoiceClient) -> None:
        vc.stop_recording()

    @bridge.bridge_command(name="connect", enabled=False)
    async def connect(self, ctx: bridge.BridgeApplicationContext | bridge.BridgeExtContext) -> None:
        if ctx.author.voice.channel:
            vc = await ctx.author.voice.channel.connect()
            await ctx.respond(content="Connected", ephemeral=True, delete_after = 5)
            await self.listen_users(vc)
            return
        await ctx.respond(content="You are not in voice channel", ephemeral=True, delete_after = 5)

    @commands.Cog.listener("on_voice_state_update")
    async def start_listen_to_users(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if (
            self.client.user
            and self.client.user.id == member.id
            and isinstance((vc := member.guild.voice_client), discord.VoiceClient)
        ):
            if vc.recording:
                await self.stop_user_listening(vc)
            # if after.channel:
            #     await self.listen_users(vc)


def setup(client: bridge.Bot):
    client.add_cog(SpeechToTextCog())
