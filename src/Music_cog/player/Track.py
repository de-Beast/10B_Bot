import datetime
from dataclasses import dataclass
from typing import Self, TypedDict

import discord

from enums import SearchPlatform

FFMPEG_OPTIONS = {
    "before_options": "\
				-reconnect 1 \
				-reconnect_streamed 1 \
				-reconnect_at_eof 1 \
				-reconnect_delay_max 2",
    "options": "-vn\
                -bufsize 16384",
}


class MetaData(TypedDict):
    title: str
    author: str
    thumbnail: str
    platform: SearchPlatform
    requested_by: discord.User | discord.Member
    requested_at: datetime.datetime


class TrackInfo(TypedDict):
    meta: MetaData
    source: str
    track_url: str
    author_url: str


@dataclass(slots=True, frozen=True)
class Track:
    src_url: str

    src: discord.FFmpegOpusAudio
    title: str
    author: str
    thumbnail: str
    track_url: str
    author_url: str

    platform: SearchPlatform
    requested_by: discord.User | discord.Member
    requested_at: datetime.datetime

    @classmethod
    async def from_dict(cls, data: TrackInfo) -> Self:
        src_url = data["source"]
        src = await discord.FFmpegOpusAudio.from_probe(data["source"], **FFMPEG_OPTIONS)
        title = data["meta"]["title"]
        author = data["meta"]["author"]
        thumbnail = data["meta"]["thumbnail"]
        platform = data["meta"]["platform"]
        requested_by = data["meta"]["requested_by"]
        requested_at = data["meta"]["requested_at"]
        track_url = data["track_url"]
        author_url = data["author_url"]
        return cls(
            src_url,
            src,
            title,
            author,
            thumbnail,
            track_url,
            author_url,
            platform,
            requested_by,
            requested_at,
        )

    @classmethod
    async def from_track(cls, track: Self | None) -> Self | None:
        if isinstance(track, Track):
            src = await discord.FFmpegOpusAudio.from_probe(track.src_url, **FFMPEG_OPTIONS)
            return cls(
                track.src_url,
                src,
                track.title,
                track.author,
                track.thumbnail,
                track.track_url,
                track.author_url,
                track.platform,
                track.requested_by,
                track.requested_at,
            )
        else:
            return None

    async def copy(self):
        return await Track.from_track(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.src_url == other.src_url
        return False

    def __str__(self) -> str:
        return f"<red>{self.title}</> @ {self.author}"
