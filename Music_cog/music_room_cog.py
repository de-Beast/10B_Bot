import json

import discord
from config import settings
from discord.ext import commands
from pandas import array

from .room.MainView import MainView
from .room.SettingsView import SettingsView

MUSIC_ROOMS_FILE_JSON = 'Music_rooms.json'
MUSIC_ROOMS_DICTS = []


def update_music_rooms_ids():
    MUSIC_ROOMS_DICTS.clear()
    with open(MUSIC_ROOMS_FILE_JSON, 'r') as f:
        data = json.load(f)
        for info in data:
            MUSIC_ROOMS_DICTS.append(info)


def add_music_room_in_db(music_room: discord.TextChannel, threads: list):
    guild: discord.Guild = music_room.guild
    data = json.load(open(MUSIC_ROOMS_FILE_JSON, 'r'))
    with open(MUSIC_ROOMS_FILE_JSON, 'w') as f:
        bUpdated = False
        for info in data:
            if guild.id == info['guild_id']:
                info['room_id'] = music_room.id
                for thread in threads:
                    info['threads'][thread[0]] = thread[1]
                bUpdated = True
                break
        if not bUpdated:
            info = {'guild_id': guild.id,
                    'room_id': music_room.id,
                    'threads': {}
                    }
            for thread in threads:
                info['threads'][thread[0]] = thread[1]
            data.append(info)
        json.dump(data, f, indent = 3)
        print(str(guild) + ' (id: ', guild.id, ') Updated Music Room!!! - new id: ', music_room.id, sep = '')
    update_music_rooms_ids()


async def update_music_rooms_db(guilds: list[discord.Guild]):
    update_music_rooms_ids()
    rooms = []
    for guild in guilds:
        for info in MUSIC_ROOMS_DICTS:
            if guild.id == info['guild_id']:
                rooms.append(info)
    f = open(MUSIC_ROOMS_FILE_JSON, 'w')
    json.dump(rooms, f, indent = 3)
    f.close()
    update_music_rooms_ids()


def get_music_room(guild: discord.Guild) -> discord.TextChannel:
    for info in MUSIC_ROOMS_DICTS:
        if guild.id == info['guild_id']:
            return guild.get_channel(info['room_id'])
    print('NO CHANNEL FOR U')
    return None


def get_thread(guild: discord.Guild, thread_type: str) -> discord.Thread:
    for info in MUSIC_ROOMS_DICTS:
        if guild.id == info['guild_id']:
            return guild.get_thread(info['threads'][thread_type])
    print('NO CHANNEL FOR U')
    return None


def check_threads(guild: discord.Guild) -> bool:
    for info in MUSIC_ROOMS_DICTS:
        if guild.id == info['guild_id']:
            for thread in get_music_room(guild).threads:
                if thread.id not in list(info['threads'].values()):
                    return False
    return True


async def get_main_message(guild: discord.Guild) -> discord.Message:
    try:
        return (await get_music_room(guild).history(limit=2, oldest_first = True).flatten())[1]
    except Exception:
        print('NO MAIN MESSAGE FOR U')
        return None


async def get_thread_message(guild: discord.Guild, thread_type: str) -> discord.Message:
    try:
        return (await get_thread(guild, thread_type).history(limit=1, oldest_first = True).flatten())[0]
    except Exception:
        print('NO THREAD MESSAGE FOR U')
        return None


class MusicRoom(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client


    async def update_main_view(self, guild: discord.Guild):
        await (await get_main_message(guild)).edit(view = MainView(self.client))


    async def update_threads_views(self, guild: discord.Guild):
        threads = ['settings_id', 'queue_id']
        for thread in threads:
            await (await get_thread_message(guild, thread)).edit(view = SettingsView(self.client))


    async def create_threads(self, room: discord.TextChannel, guild: discord.Guild) -> list:
        threads = [('settings_id', 'Settings'),
                   ('queue_id', 'Queue')]
        threads_ids = []
        for thread_info in threads:
            thread = await room.create_thread(name = thread_info[1], type = discord.ChannelType.public_thread, auto_archive_duration = 10080)
            thread.slowmode_delay = 21600
            if thread_info[1] == 'Settings':
                await thread.send(content = 'Search Platform', view = SettingsView(self.client))
            threads_ids.append((thread_info[0], thread.id))
        return threads_ids


    @commands.command(name = 'delete')
    async def delete(self, ctx: commands.Context):
        await ctx.channel.delete()


    @commands.command(name = 'create_music_room', aliases = ['create', 'make_room', 'create_room', 'make_music_room'])	
    @commands.check_any(commands.is_owner(), commands.has_guild_permissions(administrator = True))
    async def create_music_room(self, guild):
        if isinstance(guild, commands.Context):
            guild = guild.guild
        if get_music_room(guild):
            await get_music_room(guild).delete()
        room = await guild.create_text_channel(name = settings['room_name'], position = 0)
        threads = await self.create_threads(room, guild)
        gif = discord.File(open("other_files/banner.gif", 'rb'), filename = 'Banner.gif')
        embed = discord.Embed(title = 'Queue is clear', type = 'video', colour = discord.Colour(0x00FF00))
        embed.set_footer(text = 'Type the music name', icon_url = settings['back_image'])
        embed.set_image(url = settings['back_image'])
        await room.send(file = gif, embed = embed, view = MainView(self.client))
        add_music_room_in_db(room, threads)
        await room.send('Channel Created', delete_after = 5)



    @commands.command(name = 'clear_room', aliases = ['clear', 'c'])
    @commands.cooldown(3, 5)
    async def clear_room(self, ctx: commands.Context):
        room = get_music_room(ctx.guild)
        try:
            while len(await room.history(oldest_first = True).flatten()) > 3:
                try:
                    await room.purge(check = lambda m: m.author != self.client.user)
                except Exception:
                    print('Deleting messages error')
        except Exception:
            print('Unknown Channel')


    ############ Listeners ############



    @commands.Cog.listener('on_guild_join')
    async def on_guild_join(self, guild: discord.Guild):
        await self.create_music_room(guild)


    @commands.Cog.listener('on_guild_remove')
    async def on_guild_remove(self, guild: discord.Guild):
        await update_music_rooms_db(self.client.guilds)    


    @commands.Cog.listener('on_message')
    async def play_music_on_message(self, message: discord.Message):
        if not message.author.bot:
            if message.channel == get_music_room(message.guild) and not message.content.startswith(settings['prefix'], 0, len(settings['prefix'])):
                ctx = await self.client.get_context(message)
                await ctx.invoke(self.client.get_command('play'), message.content)    


    @commands.Cog.listener('on_message')
    async def clear_music_room(self, message: discord.Message):
        if message.channel == get_music_room(message.guild) and not message.author.bot:
            await self.clear_room(await self.client.get_context(message))


    @commands.Cog.listener('on_ready')
    async def check_music_rooms_in_guilds(self):
        await update_music_rooms_db(self.client.guilds)
        for guild in self.client.guilds:
            if (get_music_room(guild) is None) and check_threads(guild):
                await self.create_music_room(guild)
            try:
                await self.update_main_view(guild)
                await self.update_threads_views(guild)
            except Exception:
                break
        await self.client.when_ready()


def setup(client: commands.Bot):
	client.add_cog(MusicRoom(client))
