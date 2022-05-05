import asyncio
from json import dumps, loads
from re import fullmatch
from threading import Thread
from time import sleep

import youtube_dl
from discord.ext import commands
from vk_api import get_api

from .player.Player import Loop, Player

YDL_OPTIONS = {'format': 'bestaudio/best',
               'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
               'extractaudio': True,
			   'noplaylist': False,
      		   'writethumbnails': True,
           	   'source_address': '0.0.0.0'
               }


def search_yt_single(search_method: str):
	print('single yt')
	with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
		try:
			info = ydl.extract_info(search_method, download = False)['entries'][0]
		except Exception:
			info = ydl.extract_info(search_method, download = False)
	return {'source': info['formats'][0]['url'],
			'meta': {'title': info['title'],
            		'author': info['uploader'],
					'thumbnail': info['thumbnails'][-1]}, 
			'track_url': info['webpage_url'],
   			'author_url': info['uploader_url']}


def search_yt_list(search_method: str):
	print('list yt')
	with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
		try:
			infos = ydl.extract_info(search_method, download = False)['entries']
		except Exception:
			info = ydl.extract_info(search_method, download = False)
	for info in infos:
		yield {'source': info['formats'][0]['url'],
         		'meta': {'title': info['title'],
             			'author': info['uploader'],
						'thumbnail': info['thumbnails'][-1]},
           		'track_url': info['webpage_url'],
             	'author_url': info['uploader_url']}


def get_vk_album(owner_id: int, id: int, key):
	print('list vk')
	api = get_api()
	audios = api.method('audio.get', owner_id=owner_id, album_id=id, access_key=key)
	if audios['count'] == 0:
		return [None]
	for aud in audios['items']:
		a = get_vk_single(str(aud['owner_id'])+'_'+str(aud['id']))
		if not a:
			print(a)
			sleep(10)
			continue
		yield a


def search_vk(name) -> str | None:
	api = get_api()
	audio = api.method('audio.search', q=name, auto_complete=1)
	if audio['count'] == 0:
		return None
	return str(audio['items'][0]['owner_id']) + '_' + str(audio['items'][0]['id'])

def get_vk_single(id: str) -> dict | None | list[None]:
	print('single vk')
	if not id:
		return [None]
	api = get_api()
	audio = api.method('audio.getById', audios=id)
	if len(audio) == 0:
		return None
	return {'source': audio[0]['url'], 'meta': {'title': audio[0]['artist'] + ' — ' + audio[0]['title']}}


def define_stream_method(item: str, search_platform = 'Youtube')->list:
	yt      = fullmatch(r'https?://(?:www\.)?youtu(?:\.be|be\.com)/watch\?v=([a-zA-Z0-9]+)',                item)
	yt_list = fullmatch(r'https?://(?:www\.)?youtu(?:\.be|be\.com)/playlist\?list=([a-zA-Z0-9_\-]+)',       item)
	vk      = fullmatch(r'https?://(?:www\.)?vk\.com/audio(-?\d+_\d+)(?:_\d+)?',                            item)
	vk_list = fullmatch(r'https?://(?:www\.)?vk\.com/music/(?:playlist|album)/(-?\d+)_(\d+)_?([a-z0-9_]+)?', item)
	if not vk_list:
		vk_list = fullmatch(r'https?://(?:www\.)?vk\.com/audios\d+\?z=audio_playlist(-?\d+)_(\d+).+', item)
	if yt:
		return [search_yt_single(yt[0])]
	elif yt_list:
		return search_yt_list(yt_list[0])
	elif vk:
		return [get_vk_single(vk[1])]
	elif vk_list:
		key = vk_list[3] if len(vk_list.groups()) > 2 else None
		return get_vk_album(vk_list[1], vk_list[2], key)
	elif search_platform == 'Youtube':
		return [search_yt_single('ytsearch:' + item)]
	elif search_platform == 'VK':
		return [get_vk_single(search_vk(item))]



############################# MUSIC COG #################################


class MusicPlayerCog(commands.Cog):
	def __init__(self, client: commands.Bot):
		self.client: commands.Bot = client
		self.search_platform = 'Youtube'
		

	def set_search_platform(self, search_platform: str):
		self.search_platform = search_platform
	
	
	async def join(self, ctx: commands.Context) -> bool:
			if ctx.author.voice is None:
				await ctx.send('You are not in the voice channel', delete_after=3)
				return False
			else:
				await ctx.author.voice.channel.connect(reconnect = True, cls = Player)
				return True


############################## Checks ###################################

 
	def is_connected(self, ctx: commands.Context):
		return isinstance(ctx.voice_client, Player) and ctx.author.voice.channel == ctx.voice_client.channel

############################## Commands #################################
	

	# GROUP - PLAY
	@commands.command(name = 'play', aliases = ['p', 'add', 'paly'])
	@commands.cooldown(1, 3, commands.BucketType.default)
	async def play(self, ctx: commands.Context, *args):
		if ctx.voice_client is None:
			if not await self.join(ctx):
				return
		player: Player = ctx.voice_client
		if player.has_track() and not args:
			await ctx.invoke(self.client.get_command('pause_resume'))
			return
		elif not args:
			return
		music_name = ' '.join(args)
		async with ctx.channel.typing():
			tracks_all_meta = define_stream_method(music_name, search_platform = self.search_platform)
			# if list(tracks_all_meta) == [None]:
			# 	await ctx.send('Bruh... Something went wrong')
			# 	return None
			Thread(target = asyncio.run, args=[player.add_tracks_to_queue(tracks_all_meta)]).start()


	@commands.command(name = 'pause_resume', aliases = ['pause', 'pa', 'pas', 'resume', 'res', 're', 'toggle', 'tog'])
	@commands.check(is_connected)
	async def pause_resume(self, ctx: commands.Context):
		if self.is_connected(ctx):
			ctx.voice_client.toggle()


	@commands.command(name = 'skip', aliases = ['s', 'next'])
	@commands.check(is_connected)
	async def skip(self, ctx: commands.Context):
		if self.is_connected(ctx):
			ctx.voice_client.skip()


	@commands.command(name = 'stop')
	@commands.check(is_connected)
	async def stop(self, ctx: commands.Context):
		if self.is_connected(ctx):
			ctx.voice_client.stop()


	@commands.group(name = 'loop', aliases = ['l'])
	@commands.check(is_connected)
	async def loop(self, ctx: commands.Context):
		if self.is_connected(ctx):
			player = ctx.voice_client
			if player.looping == Loop.LOOP:
				player.set_loop(Loop.NOLOOP)
			else:
				player.set_loop(Loop.LOOP)


	@loop.command(name = 'one', aliases = ['1'])
	async def loop_one(self, ctx: commands.Context):
		ctx.voice_client.set_loop(Loop.ONE)


	@loop.command(name = 'none', aliases = ['n', 'no', 'nothing'])
	async def no_loop(self, ctx: commands.Context):
		ctx.voice_client.set_loop(Loop.NOLOOP)

	
	@commands.command(name = 'disconnect', aliases = ['dis', 'd', 'leave'])
	@commands.check(is_connected)
	async def disconnect(self, ctx: commands.Context):
		if self.is_connected(ctx):
			await ctx.voice_client.disconnect()


 	############################# Listeners #############################


	@commands.Cog.listener('on_command_error')	
	async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
		if isinstance(error, commands.CommandNotFound):
			return
		elif isinstance(error, commands.MissingRequiredArgument):
			await ctx.send('You are missing some arguments')
		elif isinstance(error, commands.BadArgument):
			await ctx.send('You are using bad arguments')
		elif isinstance(error, commands.CheckFailure):
			await ctx.send('You are not in the voice channel')
		elif isinstance(error, commands.CommandOnCooldown):
			await ctx.send('You are on cooldown')
		else:
			await ctx.send('Bruh... Something went wrong')
   
	@commands.Cog.listener('on_disconnect')
	async def disconnect(self, ctx: commands.Context):
		if ctx.voice_client is None:
			return
		else:
			await ctx.voice_client.disconnect()



def setup(client: commands.Bot):
	client.add_cog(MusicPlayerCog(client))
