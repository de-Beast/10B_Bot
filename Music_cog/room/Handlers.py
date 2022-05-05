import discord
from discord.ext import commands
from .message_config import conf
from .Views import MainView, SettingsView

class MessageHandler():
    def __init__(self, message: discord.Message):
        self.message: discord.Message = message


    @classmethod
    def create_main_view(cls, client: commands.Bot):    
        return MainView(client)





    @classmethod
    def create_embed(cls, settings: dict = None) -> discord.Embed:
        if not settings:
            settings = {'title': 'Queue is clear',
                        'type': 'video',
                        'color': 0x00FF00,
                        'footer': {'text': 'Type the music name',
                                   'icon_url': conf['back_image']},
                        'image': {'url': conf['back_image']}
                        }

        embed = discord.Embed.from_dict(settings)
        return embed


    @classmethod
    def create_file(cls, path: str = 'Music_cog/room/other_files/banner.gif',
                    name: str = 'Banner.gif') -> discord.File:
        return discord.File(open(path, 'rb'), filename = name)


    async def update_embed(self, track):
        settings = {'title': track.title,
                    'type': 'video',
                    'color': 0x00FF00,
                    'url': track.track_url,
                    'author': {'name': track.author,
                               'url': track.author_url},
                    'footer': {'text': 'Playing',
                               'icon_url': track.thumbnail},
                    'image': {'url': track.thumbnail}
                    }
        new_embed = self.create_embed(settings)
        await self.message.edit(embed = new_embed)



class ThreadHandler():
    def __init__(self, thread: discord.Thread):
        self.thread: discord.Thread = thread


    @classmethod
    def create_settings_view(cls, client: commands.Bot):
        return SettingsView(client)
