import discord
from discord import ui

from abcs import ViewABC
from enums import SearchPlatform


class SettingsView(ViewABC):
    def __init__(self, *items: ui.Item):
        super().__init__(*items, timeout=None)
        self.__search_platform: SearchPlatform = SearchPlatform.YOUTUBE

    @property
    def search_platform(self):
        return self.__search_platform

    @classmethod
    def from_message(cls, message: discord.Message) -> "SettingsView":  # type: ignore
        view: SettingsView = super().from_message(cls, message)
        for item in view.children:
            if item.custom_id == "Search Platform Select":  # type: ignore
                for option in item.options:  # type: ignore
                    if option.default:
                        view.__search_platform = SearchPlatform.get_key(option.value)
        return view

    @ui.select(
        custom_id="Search Platform Select",
        row=0,
        options=[
            discord.SelectOption(
                label="Youtube", value="yt", emoji="🐷", default=True  # Youtube
            ),
            discord.SelectOption(label="VK", value="vk", emoji="🐭"),  # VK
        ],
    )
    async def loop_callback(self, select: ui.Select, interaction: discord.Interaction):
        value = select.values[0]
        self.__search_platform = SearchPlatform.get_key(value)
        for option in select.options:
            if option.value == value:
                option.default = True
            else:
                option.default = False
        await interaction.response.edit_message(view=self)
