import discord
from discord import ui
from discord.ext import commands


class SettingsView(ui.View):
    def __init__(self, client: commands.Bot):
            super().__init__(timeout = None)
            self.client: commands.Bot = client


    @ui.select(row = 1, options = [
            discord.SelectOption( 	#Youtube
                label = 'Youtube',
                emoji = '🐷',
                default = True),
            discord.SelectOption( 	#VK
                label = 'VK',
                emoji = '🐭')
            ])  
    async def loop_callback(self, select: ui.Select, interaction: discord.Interaction):
        self.client.get_cog('Music').set_search_platform(select.values[0])
