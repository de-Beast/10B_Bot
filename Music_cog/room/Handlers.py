import discord
from discord.ext import commands

from .message_config import conf
from .Views import MainView, SettingsView


async def get_main_message(room: discord.TextChannel) -> discord.Message:
    try:
        c = 0
        async for message in room.history(limit=3, oldest_first=True):
            if c == 2:
                return message
            c += 1
    except Exception as e:
        print("NO MAIN MESSAGE FOR U @", e)
    return None


class MainMessageHandler:
    def __init__(self, room: discord.TextChannel, client: commands.Bot = None):
        self.message: discord.Message = None
        self.client: commands.Bot = client

    @classmethod
    async def init(cls, room: discord.TextChannel, client: commands.Bot = None):
        handler = cls(room, client)
        handler.message = await get_main_message(room)
        return handler

    @classmethod
    def create_main_view(cls, client: commands.Bot):
        return MainView(client)

    async def update_main_view(self):
        await self.message.edit(view=MainMessageHandler.create_main_view(self.client))

    @classmethod
    def create_embed(cls, settings: dict = None) -> discord.Embed:
        if settings is None:
            settings = {
                "title": "Queue is clear",
                "type": "video",
                "color": 0x00FF00,
                "footer": {
                    "text": "Type the music name",
                    "icon_url": conf["back_image"],
                },
                "image": {"url": conf["back_image"]},
            }

        embed = discord.Embed.from_dict(settings)
        return embed

    @classmethod
    def create_file(
        cls,
        path: str = "Music_cog/room/other_files/banner.gif",
        name: str = "Banner.gif",
    ) -> discord.File:
        return discord.File(open(path, "rb"), filename=name)

    async def update_embed(self, track=None):
        settings = None
        if track is not None:
            settings = {
                "title": track.title,
                "type": "video",
                "color": 0x00FF00,
                "url": track.track_url,
                "author": {"name": track.author, "url": track.author_url},
                "footer": {"text": "Playing", "icon_url": track.thumbnail["url"]},
                "image": {"url": track.thumbnail["url"]},
            }
        new_embed = self.create_embed(settings)
        await self.message.edit(embed=new_embed)


async def get_thread_message(thread: discord.Thread) -> discord.Message:
    try:
        return (await thread.history(limit=1, oldest_first=True).flatten())[0]
    except Exception as e:
        print("NO THREAD MESSAGE FOR U @", e)
        return None


class ThreadMessageHandler:
    def __init__(self, thread: discord.Thread, client: commands.Bot = None):
        self.thread: discord.Thread = thread
        self.client: commands.Bot = client

    @classmethod
    def create_settings_view(cls, client: commands.Bot):
        return SettingsView(client)

    async def update_threads_views(self):
        threads = ("settings_id", "queue_id")
        for thread in threads:
            thread_message = await get_thread_message(self.thread)
            if thread == "settings_id":
                await thread_message.edit(
                    view=ThreadMessageHandler.create_settings_view(self.client)
                )
