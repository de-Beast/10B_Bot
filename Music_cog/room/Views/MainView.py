from typing import Any, Union

import discord
from discord import ui

from abcs import ViewABC
from enums import Loop, Shuffle
from Music_cog.player import Player


class MainView(ViewABC):
    def __init__(self, *items: ui.Item):
        super().__init__(*items, timeout=None)
        self.__looping: Loop = Loop.NOLOOP
        self.__shuffle: Shuffle = Shuffle.NOSHUFFLE

    @property
    def looping(self):
        return self.__looping

    @property
    def shuffle(self):
        return self.__shuffle

    @classmethod
    def from_message(cls, message: discord.Message) -> "MainView":  # type: ignore
        view: MainView = super().from_message(cls, message)
        for item in view.children:
            match item.custom_id:  # type: ignore
                case "Loop Select":
                    for option in item.options:  # type: ignore
                        if option.default:
                            view.__looping = Loop.get_key(option.value)
                case "Shuffle Select":
                    for option in item.options:  # type: ignore
                        if option.default:
                            view.__shuffle = Shuffle.get_key(option.value)
        return view
    

    @ui.button(
        custom_id="Prev Button", emoji="⏮️", style=discord.ButtonStyle.primary, row=0
    )  # prev
    async def prev(self, button: ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()

    @ui.button(
        custom_id="Pause Resume Button",
        emoji="⏸",
        style=discord.ButtonStyle.success,
        row=0,
    )  # paly / pause
    async def pause_resume(self, button: ui.Button, interaction: discord.Interaction):
        if interaction.guild is not None:
            player: Union[Player, Any] = interaction.guild.voice_client
            if player is not None:
                ctx = await self.client.get_application_context(interaction)
                await self.client.get_command("pause_resume")(ctx)
                if player.is_paused():
                    button.emoji = discord.PartialEmoji.from_str("▶️")
                else:
                    button.emoji = discord.PartialEmoji.from_str("⏸")
                await interaction.response.edit_message(view=self)
                return
        await interaction.response.defer()

    @ui.button(
        custom_id="Next Button", emoji="⏭️", style=discord.ButtonStyle.primary, row=0
    )  # next
    async def next(self, button: ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        ctx = await self.client.get_application_context(interaction)
        await self.client.get_command("skip")(ctx)

    @ui.button(
        custom_id="Clear Queue Button",
        emoji="⏹️",
        style=discord.ButtonStyle.danger,
        row=0,
    )  # clear list
    async def clear(self, button: ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        ctx = await self.client.get_application_context(interaction)
        await self.client.get_command("stop")(ctx)

    @ui.select(
        custom_id="Loop Select",
        row=1,
        options=[
            discord.SelectOption(label="No Loop", emoji="🚫", default=True),  # no loop
            discord.SelectOption(label="Loop", emoji="🔁"),  # loop
            discord.SelectOption(label="Loop One", emoji="🔂"),  # loop one
        ],
    )
    async def loop_callback(self, select: ui.Select, interaction: discord.Interaction):
        value = select.values[0]
        self.__looping = Loop.get_key(value)

        player: Union[Player, Any] = None
        if interaction.guild is not None:
            player = interaction.guild.voice_client
        if player is not None:
            player.looping = self.__looping

        for option in select.options:
            if option.value == value:
                option.default = True
            else:
                option.default = False
        await interaction.response.edit_message(view=self)

    @ui.select(
        custom_id="Shuffle Select",
        row=2,
        options=[
            discord.SelectOption(  # no shuffle
                label="No Shuffle",
                emoji="🚫",
                default=True,
            ),
            discord.SelectOption(label="Shuffle", emoji="🔀"),  # shuffle
            discord.SelectOption(label="Secret Shuffle", emoji="🔒"),  # secret shuffle
        ],
    )
    async def shuffle_callback(
        self, select: ui.Select, interaction: discord.Interaction
    ):
        player: Union[Player, Any] = None
        for option in select.options:
            option.default = False
        option = select.options[0]

        if interaction.guild is not None:
            player = interaction.guild.voice_client
        if player is not None and player.has_track:
            value = select.values[0]
            self.__shuffle = Shuffle.get_key(value)
            player.shuffle = self.__shuffle
            
            match value:
                case "No Shuffle":
                    option.default = True
                case "Shuffle":
                    select.placeholder = "🔀 Queue is shuffled"
                    option.label = option.value
                case "Secret Shuffle":
                    option = select.options[2]
                    option.default = True
        else:
            option.default = True
        await interaction.response.edit_message(view=self)
