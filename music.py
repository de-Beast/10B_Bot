import discord
from discord.ext import tasks, commands
import youtube_dl
from config import settings

MUSIC_ROOMS_IDS = 'Music_rooms.txt'

class Music(commands.Cog):
	def __init__(self, client):
		self.client = client
		self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_at_eof 1 -reconnect_on_network_error 1 -reconnect_on_http_error 1 -reconnect_delay_max 2',
								'options': '-vn'}
		self.YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'} #Сделать работу с плейлистами (вроде изи)
		self.music_room = None
		self.vc = None
		self.queue = []

		self.has_track = False
		self.is_playing = False

		self.is_looping = False
		self.is_looping_one = False
		self.is_secret_shaffling = False


	def define_stream_method(self, item: str):
		if item.startswith(('https://www.youtube.com', 'https://youtu.be', 'https://youtube.com')):
			return self.search_yt(item)
		elif item.startswith(('https://vk.com/audio')):
			return False
		else:
			return self.search_yt("ytsearch:" + item)


	def search_yt(self, search_method: str):
		with youtube_dl.YoutubeDL(self.YDL_OPTIONS) as ydl:
			try:
				info = ydl.extract_info(search_method, download = False)['entries'][0]
			except Exception:
				info = ydl.extract_info(search_method, download = False)
		return {'source': info['formats'][0]['url'], 'meta': {'title': info['title']}}


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
		if self.is_looping:
			self.queue.append(self.queue[0])
		if not self.is_looping_one:
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


	async def add_reactions(self, message: discord.Message):
		await message.add_reaction('⏯️')	#paly / pause
		await message.add_reaction('⏭️')	#next
		await message.add_reaction('⏮️')	#prev
		await message.add_reaction('🔁')	#loop
		await message.add_reaction('🔂')	#loop one
		await message.add_reaction('🔀')	#shuffle
		await message.add_reaction('🔣')	#secret shuffle
		await message.add_reaction('⏹️')	#clear list


	async def play_pause_reaction(self):
		if self.is_playing:
			ctx = await self.client.get_context(await self.music_room.send('Paused'))
		else:
			ctx = await self.client.get_context(await self.music_room.send('Resumed'))
		await ctx.invoke(self.client.get_command('pause_resume'))


	async def skip_reaction(self):
		ctx = await self.client.get_context(await self.music_room.send('Skiped'))
		await ctx.invoke(self.client.get_command('skip'))


	async def prev_track_reaction(self):
		pass


	async def loop_reaction(self):
		pass


	async def loop_one_reaction(self):
		pass


	async def shuffle_reaction(self):
		pass


	async def secret_shuffle_reaction(self):
		pass


	async def stop_reaction(self):
		pass



############################## Checks ###################################



############################## Commands #################################
	

					####### Music Commands #######
	# GROUP - PLAY
	@commands.group(name = 'play', aliases = ['p', 'add', 'paly'])
	@commands.cooldown(1, 3, commands.BucketType.default)
	async def play(self, ctx, *args):
		if len(self.client.voice_clients) == 0 and not await ctx.invoke(self.client.get_command('join')):
			await ctx.send('Bruh... Something went wrong')
			return None
		if self.has_track and not bool(args):
			await ctx.invoke(self.client.get_command('pause'))
			return None
		music_name = ' '.join(args)
		async with ctx.channel.typing():
			track_all_meta = self.define_stream_method(music_name)
			track = {'source': await discord.FFmpegOpusAudio.from_probe(track_all_meta['source'], **self.FFMPEG_OPTIONS), 'meta': track_all_meta['meta']}
			if not bool(track):
				await ctx.send('Unexpected error', delete_after = 5)
			else:
				self.queue.append(track)
				await ctx.send('Added ' + track['meta']['title'], delete_after = 5)
				print(*self.queue)
			if not self.has_track:
				self.play_next()


	@commands.command(name = 'skip', aliases = ['s'])
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


	@commands.command(name = 'loop', aliases = ['l'])
	async def loop(self, ctx):
		self.is_looping = not self.is_looping


	@commands.command(name = 'loop_one', aliases = ['lo', 'lone'])
	async def loop_one(self, ctx):
		self.is_looping_one = not self.is_looping_one

	
	@commands.command(name = 'pause_resume', aliases = ['pause', 'pa', 'pas', 'resume', 'res', 're', 'toggle', 'tog'])
	async def pause_resume(self, ctx):
		if self.has_track:
			if self.is_playing:
				self.vc.pause()
				self.is_playing = False
			else:
				self.vc.resume()
				self.is_playing = True
	

	@commands.command(name = 'join', aliases = ['j'], delete_after = 5)
	async def join(self, ctx):
		if ctx.author.voice is None:
			await ctx.send('You are not in the voice channel')
			return False
		else:
			self.vc = await ctx.author.voice.channel.connect()
			return True


	@commands.command(name = 'disconnect', aliases = ['dis', 'd'])
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
		#TODO #embed_banner = discord.Embed.from_dict({'title': 'Queue is clear', 'type': 'video', 'colour': {'r': 0, 'g': 255, 'b': 0}, 'footer': {'text': 'Type the music name', 'icon_url': settings['back_image']}, 'image': {'url': settings['back_image']}})
		embed_banner = discord.Embed(title = 'Queue is clear', type = 'video', colour = discord.Colour(0x00FF00))
		embed_banner.set_footer(text = 'Type the music name', icon_url = settings['back_image'])
		embed_banner.set_image( url = settings['back_image'] )
		message = await room.send(embed = embed_banner)
		await self.add_reactions(message)
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


	@commands.Cog.listener('on_reaction_add')
	async def pressed_reaction(self, reaction, user):
		if reaction.emoji == "⏯️":
			pass
		if reaction.emoji == "⏭️":
			pass
		if reaction.emoji == "⏮️":
			pass
		if reaction.emoji == "🔁":
			pass
		if reaction.emoji == "🔂":
			pass
		if reaction.emoji == "🔀":
			pass
		if reaction.emoji == "🔣":
			pass
		if reaction.emoji == "⏹️":
			pass







def setup(client):
	client.add_cog(Music(client))

