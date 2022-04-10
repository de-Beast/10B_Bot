from json import dumps, loads
from re import fullmatch
from threading import Thread
from time import sleep


import asyncio
import discord
import youtube_dl
from discord import ui
from discord.ext import bridge, commands
from requests import get, post
from enum import Enum

from config import settings
from vk_api import get_api

MUSIC_ROOMS_IDS = 'Music_rooms.txt'

Loop = Enum('Loop', 'NOLOOP LOOP ONE', start = 0)
YDL_OPTIONS = {
			'format': 'bestaudio',
			'noplaylist': 'False'}





def search_yt_single(search_method: str):
	print('single')
	with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
		try:
			info = ydl.extract_info(search_method, download = False)['entries'][0]
		except Exception:
			info = ydl.extract_info(search_method, download = False)
	return {'source': info['formats'][0]['url'], 'meta': {'title': info['title']}}

def search_yt_list(search_method: str):
	print('list')
	with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
		try:
			infos = ydl.extract_info(search_method, download = False)['entries']
		except Exception:
			info = ydl.extract_info(search_method, download = False)
	print(infos)
	for info in infos:
		yield {'source': info['formats'][0]['url'], 'meta': {'title': info['title']}}


def get_vk_album(owner_id: int, id: int, key)->dict:
	api = get_api()
	audios = api.method('audio.get', owner_id=owner_id, album_id=id, access_key=key)
	if audios['count'] == 0:
		return [None]
	for aud in audios['items']:
		a = get_vk_audio(str(aud['owner_id'])+'_'+str(aud['id']))
		if not a:
			print(a)
			sleep(10)
			continue
		yield a


def search_vk(name):
	api = get_api()
	audio = api.method('audio.search', q=name, auto_complete=1)
	if audio['count'] == 0:
		return None
	return str(audio['items'][0]['owner_id']) + '_' + str(audio['items'][0]['id'])

def get_vk_audio(id: str)->dict:
	if not id:
		return [None]
	api = get_api()
	audio = api.method('audio.getById', audios=id)
	if len(audio) == 0:
		return None
	return {'source': audio[0]['url'], 'meta': {'title': audio[0]['artist'] + ' — ' + audio[0]['title']}}


# get_vk_audio(search_vk('мэшап оксимирон'))
def define_stream_method(item: str, use_yt = True)->list:
	yt = fullmatch(r'https?://(?:www\.)?youtu(?:\.be|be\.com)/watch\?v=([a-zA-Z0-9]+)', item)
	yt_list = fullmatch(r'https?://(?:www\.)?youtu(?:\.be|be\.com)/playlist\?list=([a-zA-Z0-9_\-]+)', item)
	vk = fullmatch(r'https?://(?:www\.)?vk\.com/audio(-?\d+_\d+)(?:_\d+)?', item)
	vk_list = fullmatch(r'https?://(?:www\.)?vk\.com/music/(?:playlist|album)/(-?\d+)_(\d+)_?([a-z0-9]+)?', item)
	if not vk_list:
		vk_list = fullmatch(r'https?://(?:www\.)?vk\.com/audios\d+\?z=audio_playlist(-?\d+)_(\d+).+', item)
	if yt:
		return [search_yt_single(yt[0])]
	elif yt_list:
		return search_yt_list(yt_list[0])
	elif vk:
		return [get_vk_audio(vk[1])]
	elif vk_list:
		key = vk_list[3] if len(vk_list.groups()) > 2 else None
		return get_vk_album(vk_list[1], vk_list[2], key)
	elif use_yt:
		return [search_yt_single("ytsearch:" + item)]
	else:
		return [get_vk_audio(search_vk(item))]



class Music(commands.Cog):
	def __init__(self, client):
		self.client = client
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
		# TODO: Сделать работу с плейлистами (вроде изи)
		self.music_room = None
		self.vc = None
		self.queue = []
		self.main_message = None

		self.has_track = False
		self.is_playing = False

		
		self.looping = Loop.NOLOOP
		self.is_secret_shaffling = False
	

	def play_next(self):
		if len(self.queue) > 0:
			track = self.queue[0]['source']
			self.has_track = True
			self.is_playing = True
			self.update_queue()
			self.vc.play(track, after = lambda a: self.play_next())
		else:
			self.vc.stop()
			self.is_playing = False
			self.has_track = False


	def update_queue(self):
		if self.looping == Loop.LOOP:
			self.queue.append(self.queue[0])
		elif self.looping == Loop.NOLOOP:
			self.queue.pop(0)
	

	def init_music_room(self, guild):
		room_id = self.check_rooms_ids(guild)
		if type(room_id) == int:
			self.music_room = guild.get_channel(room_id)
			return False
		return True


	def check_rooms_ids(self, guild):
			room_id = None
			with open(MUSIC_ROOMS_IDS, 'r+') as Rooms:
				for info in Rooms.readlines():
					if guild.id == int(info.split()[0]):
						room_id = int(info.split()[1])
						break
				if room_id is None:
					return False
			for channel in guild.text_channels:
				if channel.id == room_id:
					return room_id
			return False


	def update_music_rooms(self, guild):
		with open(MUSIC_ROOMS_IDS, 'r+') as Rooms:
			for info in Rooms.readlines():
				if guild.id == int(info.split()[0]):
					Rooms.seek(Rooms.tell() - len(info) - 1)
					Rooms.write(str(guild.id) + ' ' + str(self.music_room.id) + '\n')
					print(str(guild) + '(id: ' + str(guild.id) + ') Updated Music Room!!! - new id: ' + str(self.music_room.id))
					break
				Rooms.write(str(guild.id) + ' ' + str(self.music_room.id) + '\n')
				print(str(guild) + ' (id: ' + str(guild.id) + ') Updated Music Room!!! - new id: ' + str(self.music_room.id))


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
			if not self.has_track:
				self.play_next()
			sleep(0.75)

	class MainView(ui.View):
		def __init__(self, client):
			super().__init__(timeout = None)
			self.client = client

		@ui.button(emoji = '⏮️', style = discord.ButtonStyle.primary, row = 0) #prev
		async def prev(self, button, interaction):
			pass


		@ui.button(emoji = '⏯️', style = discord.ButtonStyle.success, row = 0) #paly / pause
		async def pause_resume(self, button, interaction):
			ctx = await self.client.get_context(interaction.message)
			await ctx.invoke(self.client.get_command('pause_resume'))

		@ui.button(emoji = '⏭️', row = 0) #next
		async def next(self, button, interaction):
			ctx = await self.client.get_context(interaction.message)
			await ctx.invoke(self.client.get_command('skip'))

		@ui.button(emoji = '⏹️', style = discord.ButtonStyle.danger, row = 0) #clear list
		async def clear(self, button, interaction):
			ctx = await self.client.get_context(interaction.message)
			await ctx.invoke(self.client.get_command('stop'))

		@ui.select( row = 1, options = [
			discord.SelectOption( 	#no loop
				label = 'No Loop',
				default = True),
			discord.SelectOption( 	#loop
				label = 'Loop',
				emoji = '🔁'),
			discord.SelectOption( 	#loop one
				label = 'Loop One',
				emoji = '🔂')])
		async def loop_callback(self, option, interaction):
			ctx = await self.client.get_context(interaction.message)
			if option.value == 'No Loop':
				ctx.invoke(self.client.get_command('loop none'))
			if option.values[0] == 'Loop':
				ctx.invoke(self.client.get_command('loop'))
			elif option.value == 'Loop One':
				ctx.invoke(self.client.get_command('loop one'))


		@ui.select( row = 2, options = [
			discord.SelectOption( 	#no shuffle
				label = 'No Shuffle',
				default = True),
			discord.SelectOption( 	#shuffle
				label = 'Shuffle',
				emoji = '🔀'),
			discord.SelectOption( 	#secret shuffle
				label = 'Secret Shuffle',
				emoji = '🔒')])
		async def shuffle_callback(self, option, interaction):
			ctx = await self.client.get_context(interaction.message)
			if option.values[0] == 'Shuffle':
				await ctx.invoke(self.client.get_command('shuffle'))
			# elif option.value == 'Shuffling':
			# 	await ctx.invoke(self.client.get_command('shuffling'))



	async def add_menu(self, message: discord.Message):
		await message.edit(view = self.MainView(self.client))


	async def change_main_message(self):
		new_embed = discord.Embed(title = 'Queue is clear', type = 'video', colour = discord.Colour(0x00FF00))
		discord.Button



############################## Checks ###################################



############################## Commands #################################
	

					####### Music Commands #######
	# GROUP - PLAY
	@commands.command(name = 'play', aliases = ['p', 'add', 'paly'])
	@commands.cooldown(1, 3, commands.BucketType.default)
	async def play(self, ctx, *args):
		if len(self.client.voice_clients) == 0 and not await ctx.invoke(self.client.get_command('join')):
			ctx.send('Bruh... Something went wrong')
			return None
		if self.has_track and not args:
			ctx.invoke(self.client.get_command('pause_resume'))
			return None
		# elif not self.has_track:
		# 	return None
		music_name = ' '.join(args)
		async with ctx.channel.typing():
			tracks_all_meta = define_stream_method(music_name)
			# if list(tracks_all_meta) == [None]:
			# 	await ctx.send('Bruh... Something went wrong')
			# 	return None
			Thread(target = asyncio.run, args=[self.add_tracks_to_queue(ctx, tracks_all_meta)]).start()


	@commands.command(name = 'vk')
	async def play_vk(self, ctx, *args):
		if len(self.client.voice_clients) == 0 and not await ctx.invoke(self.client.get_command('join')):
			ctx.send('Bruh... Something went wrong')
			return None
		if self.has_track and not args:
			ctx.invoke(self.client.get_command('pause_resume'))
			return None
		# elif not self.has_track:
		# 	return None
		music_name = ' '.join(args)
		async with ctx.channel.typing():
			tracks_all_meta = define_stream_method(music_name, use_yt = False)
			# if list(tracks_all_meta) == [None]:
			# 	await ctx.send('Bruh... Something went wrong')
			# 	return None
			Thread(target = asyncio.run, args=[self.add_tracks_to_queue(ctx, tracks_all_meta)]).start()


	@commands.command(name = 'skip', aliases = ['s', 'next'])
	async def skip(self, ctx):
		self.vc.pause()
		self.is_playing = False
		self.play_next()


	@commands.command(name = 'stop')
	async def stop(self, ctx):
		self.vc.stop()
		self.is_playing = False
		self.has_track = False
		self.queue = []


	# @commands.group(name = 'loop', aliases = ['l'])
	# async def loop(self, ctx):
	# 	if self.looping == Loop.LOOP:
	# 		self.looping = Loop.NOLOOP
	# 	else:
	# 		self.looping = Loop.LOOP

	# @loop.command(name = 'one', aliases = ['1'])
	# async def loop_one(self, ctx):
	# 	self.looping = Loop.ONE
	# 	await ctx.send('Looping one')


	# @loop.command(name = 'none', aliases = ['n', 'no', 'nothing'])
	# async def no_loop(self, ctx):
	# 	self.looping = Loop.NOLOOP
	# 	await ctx.send('No loop')

	
	@commands.command(name = 'pause_resume', aliases = ['pause', 'pa', 'pas', 'resume', 'res', 're', 'toggle', 'tog'])
	async def pause_resume(self, ctx):
		if self.has_track:
			if self.is_playing:
				self.vc.pause()
			else:
				self.vc.resume()
			self.is_playing = not self.is_playing
	

	@commands.command(name = 'join', aliases = ['j'], delete_after = 5)
	async def join(self, ctx):
		if ctx.author.voice is None:
			await ctx.send('You are not in the voice channel')
			return False
		else:
			self.vc = await ctx.author.voice.channel.connect()
			return True


	@commands.command(name = 'disconnect', aliases = ['dis', 'd', 'leave'])
	async def disconnect(self, ctx):
		await ctx.voice_client.disconnect()
		self.vc = None
		self.is_playing = False
		self.has_track = False

	

					####### Room Commands #######



	@commands.command(name = 'create_music_room', aliases = ['create', 'make_room', 'create_room', 'make_music_room'])	
	@commands.check_any(commands.is_owner(), commands.has_guild_permissions(administrator = True))
	async def create_music_room(self, ctx):
		if self.music_room is not None:
			await self.music_room.delete()
		if type(ctx) != discord.Guild:
			self.music_room = await ctx.guild.create_text_channel(name = settings['room_name'], position = 0)
		else:
			self.music_room = await ctx.create_text_channel(name = settings['room_name'], position = 0)
		self.update_music_rooms(self.music_room.guild)
		room = self.music_room
		gif = open("other_files/banner.gif", 'rb')
		await room.send(file = discord.File(gif, filename = 'Banner.gif'))
		embed = discord.Embed(title = 'Queue is clear', type = 'video', colour = discord.Colour(0x00FF00))
		embed.set_footer(text = 'Type the music name', icon_url = settings['back_image'])
		embed.set_image(url = settings['back_image'])
		self.main_message = message = await room.send(embed = embed)
		await self.add_buttons(message)
		await room.send('Channel Created', delete_after = 5)


	
	@commands.command(name = 'clear_room', aliases = ['clear', 'c'])
	@commands.cooldown(3, 5)
	async def clear_room(self, ctx):
		c = 0
		history = await self.music_room.history(oldest_first = True).flatten()
		for message in history:
			if c > 1:
				try:
					await message.delete()
				except Exception:
					print('Message not Found')
			c += 1

############################## Reactions #################################





############################## Listeners #################################

	
	@commands.Cog.listener('on_voice_state_update')
	async def update_bot_vc(self, member, before, after):
		if member.bot:
			self.vc = None


	@commands.Cog.listener()
	async def on_guild_join(self, ctx):
		await ctx.invoke(self.client.get_command('create_music_room'))

	
	@commands.Cog.listener('on_message')
	async def play_music_on_message(self, message):
		if not message.author.bot:
			if message.channel == self.music_room and not message.content.startswith(settings['prefix'], 0, len(settings['prefix'])):
				ctx = await self.client.get_context(message)
				await ctx.invoke(self.client.get_command('play'), message.content)


	@commands.Cog.listener('on_message')
	async def clear_music_room(self, message):
		if message.channel == self.music_room:
			await self.clear_room(message)


	@commands.Cog.listener('on_message')
	async def set_music_room_on_message(self, message):
		if self.music_room == None:
			if self.init_music_room(message.guild):
				ctx = await self.client.get_context(message)
				await ctx.invoke(self.client.get_command('create_music_room'))



def setup(client):
	client.add_cog(Music(client))

