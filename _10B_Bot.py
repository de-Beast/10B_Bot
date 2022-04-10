import discord
from discord import ui
from discord.ext import commands, bridge

import music
from vk_api import get_api
from config import settings

# TODO: 
# [ ] Разбить код на файлы
# [ ] Отображение очереди
# [ ] Ставить плейлисты в очереди
# [ ] Сделать кнопки рабочими
# [ ] Мб решить проблему с капчами

music_room_name = settings['room_name']
music_room = None
client = commands.Bot(command_prefix = settings['prefix'], intents = discord.Intents.all())
api = get_api(settings['vkadmin_token'])

cogs = [music]
for i in range(len(cogs)):
	cogs[i].setup(client)

@client.command(name = 'voice', aliases = ['v'], case_insensitive = True)
async def voice(ctx):
	print('i am Bot')

@client.command(name = 'puk')
async def lol(ctx):
	button1 = ui.Button(style = discord.ButtonStyle.primary, emoji = '❤️')
	v = ui.View(button1)
	await ctx.send(view = v)



@client.event
async def on_ready():
	for guild in client.guilds:
		await guild.text_channels[0].send('Online', delete_after = 1)
	print(*client.guilds)
	print("Bot is ready")


client.run(settings['token'])
