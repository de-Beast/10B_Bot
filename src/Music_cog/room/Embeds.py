import random
from typing import Self

import discord

from .message_config import message_config
from enums import Shuffle, ThreadType
from Music_cog import Utils
from Music_cog.player.Track import Track

def rofl(requester: discord.User | discord.Member) -> str:
    rofl_str = " – "
    match requester.id:
        case 447849746586140672:
            rofl_str += random.choice(("ПОПУЩЕНЕЦ", "ОБСОСИК", "БЕРСЕРК ГАВНИЩЕ ЕБУЧЕЕ"))
        case 446753575465385998:
            rofl_str += random.choice(
                (
                    "ВОТ БЫ ТЫ НЕ РАЗГОВАРИВАЛ",
                    "ЖИРНОЕ ЧМО",
                    "КАКАЯ ЖЕ НАСТЕНЬКА ОХУИТЕЛЬНАЯ",
                )
            )
        case 309011989286354944:
            rofl_str += random.choice(("МОЯ СЛАДЕНЬКАЯ БУЛОЧКА", "АНИМЕШНИК", "ТРАХНИ МЕНЯ"))
        case 600361186495692801:
            rofl_str += random.choice(("ЛУЧШИЙ В МИРЕ", "СПАСИБО ЗА БОТА", "АПНУЛ ВТОРУЮ ПЛАТИНУ"))
    return rofl_str if len(rofl_str) > 3 else ""

class Embed(discord.Embed):
    def update(self, embed: Self, *, is_completely: bool = False) -> None:
        for slot in self.__slots__:
            if (value := getattr(embed, slot)) is not None and value is not Embed.Empty or is_completely:
                setattr(self, slot, value)


class EmbedDefault(Embed):
    def __init__(self, guild: discord.Guild | None, shuffle: Shuffle = Shuffle.NOSHUFFLE, **kwargs) -> None:
        super().__init__(**kwargs)
        self.title = "Queue is clear"
        self.set_image(url=message_config["back_image"])
        self.type = "rich"
        self.colour = discord.Colour(0x00FF00)
        match shuffle:
            case Shuffle.NOSHUFFLE:
                self.set_footer(text="Using default queue")
            case Shuffle.SHUFFLE:
                self.set_footer(text="Using shuffled queue")
            case Shuffle.SECRET:
                self.set_footer(text="Using secretly shuffled queue")
        if guild:
            self.description = "|"
            for thread_type in ThreadType:
                thread = Utils.get_thread(guild, thread_type)
                self.description += f" [{thread_type.name.lower()}]({thread.jump_url}) |" if thread else ""


class EmbedTrack(EmbedDefault):
    def __init__(self, track: Track, number: int | None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.title = track.title
        self.timestamp = track.requested_at
        self.url = track.track_url
        self.set_author(name=f"{number}. {track.author}" if number else f"{track.author}",
                        url=track.author_url
                        )
        self.description = f"Requested by {track.requested_by.mention}{rofl(track.requested_by)}\n\
                            <t:{track.requested_at.timestamp().__ceil__()}:R>"
