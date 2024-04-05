from typing import Any, Mapping, Self

import discord

from enums import ThreadType
from Music_cog import Utils
from Music_cog.player.Track import Track

from .message_config import message_config


def update_discription_from_track(embed: discord.Embed, track: Track) -> discord.Embed:
    embed.timestamp = track.requested_at
    embed.description = (
        f"Requested by {track.requested_by.mention} <t:{track.requested_at.timestamp().__ceil__()}:R>\n"
        f"Platform: {track.platform.value}"
    )
    return embed


class EmbedDefault(discord.Embed):
    def __init__(
        self,
        guild: discord.Guild | None = None,
        color: discord.Colour | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.title = "Queue is clear"
        self.set_image(url=message_config["back_image"])
        self.type = "rich"
        self.colour = color if color else discord.Colour(0x00FF00)
        if guild:
            self._set_thread_links_in_description(guild)

    @classmethod
    async def create_with_updated_footer(
        cls, guild: discord.Guild, *args, **kwargs
    ) -> Self:
        self = cls(guild, *args, **kwargs)
        await self.update_footer(guild)
        return self

    @classmethod
    async def from_dict_with_updated_footer(
        cls, data: Mapping[str, Any], guild: discord.Guild | None
    ) -> Self:
        self = super().from_dict(data)
        await self.update_footer(guild)
        return self

    async def update_footer(self, guild: discord.Guild | None) -> None:
        from Music_cog.room.Handlers import SettingsThreadHandler

        if (thread := Utils.get_thread(guild, ThreadType.SETTINGS)) and (
            handler := SettingsThreadHandler(thread)
        ):
            self.set_footer(
                text=f"Default search platform: {(await handler.get_search_platform()).value}"
            )

    def _set_thread_links_in_description(self, guild: discord.Guild):
        self.description = "|"
        for thread_type in ThreadType:
            thread = Utils.get_thread(guild, thread_type)
            self.description += (
                f" [{thread_type.name.lower()}]({thread.jump_url}) |" if thread else ""
            )


class EmbedTrack(EmbedDefault):
    def __init__(
        self,
        track: Track,
        number: int | None = None,
        color: discord.Colour | None = None,
        guild: discord.Guild | None = None,
        **kwargs,
    ) -> None:
        super().__init__(guild, color if color else discord.Colour.dark_grey(), **kwargs)
        self.remove_image()

        self.title = track.title
        self.timestamp = track.requested_at
        self.url = track.track_url
        self.set_author(
            name=f"{number}. {track.author}" if number else f"{track.author}",
            url=track.author_url,
        )
        self.description = (
            f"Requested by {track.requested_by.mention} <t:{track.requested_at.timestamp().__ceil__()}:R>\n"
            f"Platform: {track.platform.value}"
        )

    @staticmethod
    def update_color(embed: "EmbedTrack", *, is_playing: bool = True) -> "EmbedTrack":
        embed.colour = discord.Colour(0x00FF00) if is_playing else discord.Colour.dark_grey()
        return embed


class EmbedPlayer(EmbedTrack):
    def __init__(
        self,
        guild: discord.Guild,
        track: Track,
        color: discord.Colour = discord.Colour(0x00FF00),
        **kwargs,
    ) -> None:
        super().__init__(track, None, color, guild, **kwargs)
        self._set_thread_links_in_description(guild)

        self.set_image(
            url=track.thumbnail if track.thumbnail else message_config["back_image"]
        )
        self.add_field(
            name="Request Info",
            inline=True,
            value=(
                f"Requested by {track.requested_by.mention} <t:{track.requested_at.timestamp().__ceil__()}:R>\n"
                f"Platform: {track.platform.value}"
            ),
        )
