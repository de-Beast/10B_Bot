import discord
from discord import ui
from discord.ext import commands


class MainView(ui.View):
    def __init__(self, client: commands.Bot):
        super().__init__(timeout = None)
        self.client: commands.Bot = client
        
    
    @ui.button(emoji = "⏮️", style = discord.ButtonStyle.primary, row = 0) #prev
    async def prev(self, button: ui.Button, interaction: discord.Interaction):
        pass


    @ui.button(emoji = '⏸', style = discord.ButtonStyle.success, row = 0) #paly / pause
    async def pause_resume(self, button: ui.Button, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if isinstance(player, discord.VoiceClient):
            ctx = await self.client.get_application_context(interaction)
            await ctx.invoke(self.client.get_command('pause_resume'))
            if player.is_paused():
                button.emoji = '▶️'
            else:
                button.emoji = '⏸'
            await interaction.response.edit_message(view = self)
        

    @ui.button(emoji = '⏭️', style = discord.ButtonStyle.primary, row = 0) #next
    async def next(self, button: ui.Button, interaction: discord.Interaction):
        ctx = await self.client.get_application_context(interaction)
        await ctx.invoke(self.client.get_command('skip'))


    @ui.button(emoji = '⏹️', style = discord.ButtonStyle.danger, row = 0) #clear list
    async def clear(self, button: ui.Button, interaction: discord.Interaction):
        ctx = await self.client.get_application_context(interaction)
        await ctx.invoke(self.client.get_command('stop'))




