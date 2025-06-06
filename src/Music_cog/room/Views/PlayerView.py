from typing import Any, Self

import discord
from discord import ui

from ABC import ViewABC
from enums import Loop, Shuffle
from Music_cog import player as plr


class PlayerView(ViewABC):
    def __init__(self, *items: ui.Item, timeout=None, disable_on_timeout=False):
        super().__init__(*items, timeout=timeout, disable_on_timeout=disable_on_timeout)
        self.__loop: Loop = Loop.NOLOOP
        self.__shuffle: Shuffle = Shuffle.NOSHUFFLE

    @property
    def loop(self) -> Loop:
        return self.__loop

    @property
    def shuffle(self) -> Shuffle:
        return self.__shuffle

    @classmethod
    def from_message(
        cls, message: discord.Message, /, *, timeout: float | None = None
    ) -> Self:
        view: Self = super().from_message(message, timeout=timeout)
        for item in view.children:
            if not isinstance(item, ui.Select):
                continue

            match item.custom_id:
                case "Loop Select":
                    for option in item.options:
                        if option.default:
                            view.__loop = Loop.get_key(option.value)

                case "Shuffle Select":
                    for option in item.options:
                        if option.default:
                            view.__shuffle = Shuffle.get_key(option.value)
        return view

    def set_to_default_view(self, only_play_pause_button: bool = False) -> None:
        for item in self.children:
            if isinstance(item, ui.Button) and item.custom_id == "Pause Resume Button":
                item.emoji = discord.PartialEmoji.from_str("⏸️")
            elif isinstance(item, ui.Select) and item.custom_id == "Shuffle Select":
                if not only_play_pause_button:
                    item.options[0].default = True

    @ui.button(
        custom_id="Prev Button", emoji="⏮️", style=discord.ButtonStyle.primary, row=0
    )  # prev
    async def prev_callback(self, button: ui.Button, interaction: discord.Interaction):
        if interaction.guild is not None:
            player: plr.MusicPlayer | Any = interaction.guild.voice_client
            if isinstance(player, plr.MusicPlayer):
                player.prev()
                self.set_to_default_view(only_play_pause_button=True)
                await interaction.response.edit_message(view=self)
                return
        await interaction.response.defer()

    @ui.button(
        custom_id="Repeat Button", emoji="↩️", style=discord.ButtonStyle.primary, row=0
    )  # repeat
    async def repeat_callback(
        self, button: ui.Button, interaction: discord.Interaction
    ):
        if interaction.guild is not None:
            player: plr.MusicPlayer | Any = interaction.guild.voice_client
            if isinstance(player, plr.MusicPlayer):
                player.repeat_current()
                self.set_to_default_view(only_play_pause_button=True)
                await interaction.response.edit_message(view=self)
                return
        await interaction.response.defer()

    @ui.button(
        custom_id="Pause Resume Button",
        emoji="⏸️",
        style=discord.ButtonStyle.success,
        row=0,
    )  # paly / pause
    async def pause_resume_callback(
        self, button: ui.Button, interaction: discord.Interaction
    ):
        if interaction.guild is not None:
            player: plr.MusicPlayer | Any = interaction.guild.voice_client
            if isinstance(player, plr.MusicPlayer):
                player.toggle()
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
    async def next_callback(self, button: ui.Button, interaction: discord.Interaction):
        if interaction.guild is not None:
            player: plr.MusicPlayer | Any = interaction.guild.voice_client
            if isinstance(player, plr.MusicPlayer):
                player.skip()
                self.set_to_default_view(only_play_pause_button=True)
                await interaction.response.edit_message(view=self)
                return
        await interaction.response.defer()

    @ui.button(
        custom_id="Clear Queue Button",
        emoji="⏹️",
        style=discord.ButtonStyle.danger,
        row=0,
    )  # clear list
    async def clear_callback(self, button: ui.Button, interaction: discord.Interaction):
        if interaction.guild is not None:
            player: plr.MusicPlayer | Any = interaction.guild.voice_client
            if isinstance(player, plr.MusicPlayer):
                await player.stop_player()
        await interaction.response.defer()

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
        self.__loop = Loop.get_key(value)

        if interaction.guild is not None:
            player: plr.MusicPlayer | Any = interaction.guild.voice_client
            if isinstance(player, plr.MusicPlayer):
                player.looping = self.__loop

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
        ],
    )
    async def shuffle_callback(
        self, select: ui.Select, interaction: discord.Interaction
    ):
        option = select.options[0]
        if interaction.guild is not None:
            player: plr.MusicPlayer | Any = interaction.guild.voice_client
            if isinstance(player, plr.MusicPlayer):
                if not player.is_playing_or_paused:
                    await interaction.response.edit_message(view=self)
                    return
                
                for opt in select.options:
                    opt.default = False
                
                value = select.values[0]
                self.__shuffle = Shuffle.get_key(value)

                match value:
                    case "No Shuffle":
                        option.default = True
                    case "Shuffle":
                        select.placeholder = "🔀 Queue is shuffled"
                await interaction.response.edit_message(view=self)
                await player.set_shuffle(self.__shuffle)
                return

        option.default = True
        await interaction.response.edit_message(view=self)
