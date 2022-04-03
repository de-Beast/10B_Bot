import discord
from discord.ext import tasks, commands
from config import settings
import music

music_room_name = settings['room_name']
music_room = None
client = commands.Bot(command_prefix = settings['prefix'], intents = discord.Intents.all())

cogs = [music]
for i in range(len(cogs)):
	cogs[i].setup(client)


@client.command(name = 'voice', aliases = ['v'], case_insensitive = True)
async def voice(ctx):
	print('i am Bot')


""" @client.after_invoke
async def lol(ctx):
	print('lol') """

@client.event
async def on_ready():
	for guild in client.guilds:
		await guild.text_channels[0].send('Online', delete_after = 1)
	print(*client.guilds)
	print("Bot is ready")


client.run(settings['token'])