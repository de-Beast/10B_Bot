from typing import Self

import discord
from discord import ui

from ABC import ViewABC
from enums import SearchPlatform
from Music_cog import Utils
from Music_cog.room import Handlers
from Music_cog.room.Embeds import EmbedDefault


class SettingsView(ViewABC):
    def __init__(self, *items: ui.Item, timeout=None, disable_on_timeout=False):
        super().__init__(*items, timeout=timeout, disable_on_timeout=disable_on_timeout)
        self.__search_platform: SearchPlatform = SearchPlatform.YOUTUBE

    @property
    def search_platform(self):
        return self.__search_platform

    @classmethod
    def from_message(
        cls, message: discord.Message, /, *, timeout: float | None = None
    ) -> Self:
        view: Self = super().from_message(message, timeout=timeout)
        for item in view.children:
            if (
                isinstance(item, ui.Select)
                and item.custom_id == "Search Platform Select"
            ):
                for option in item.options:
                    if option.default:
                        view.__search_platform = SearchPlatform.get_key(option.value)
        return view

    @ui.select(
        custom_id="Search Platform Select",
        row=1,
        options=[
            discord.SelectOption(
                label="Youtube",
                value=SearchPlatform.YOUTUBE.value,
                emoji="🐷",
                default=True,  # Youtube
            ),
            discord.SelectOption(
                label="VK", value=SearchPlatform.VK.value, emoji="🐭"
            ),  # VK
        ],
    )
    async def search_platform_callback(
        self, select: ui.Select, interaction: discord.Interaction
    ):
        value = select.values[0]
        self.__search_platform = SearchPlatform.get_key(value)
        for option in select.options:
            if option.value == value:
                option.default = True
            else:
                option.default = False

        await interaction.response.edit_message(view=self)

        if (
            handler := await Handlers.PlayerMessageHandler.from_room(
                Utils.get_music_room(interaction.guild)
            )
        ) and len(handler.message.embeds) > 0:
            embed = handler.message.embeds[0]
            await handler.message.edit(
                embed=await EmbedDefault.from_dict_with_updated_footer(
                    embed.to_dict(), interaction.guild
                )
            )
