from dataclasses import dataclass
from typing import Optional, TypedDict

import discord

FFMPEG_OPTIONS = {
    "before_options": "\
				-reconnect 1 \
				-reconnect_streamed 1 \
				-reconnect_at_eof 1 \
				-reconnect_delay_max 2",
    "options": "-vn\
                -bufsize 8192",
}


class MetaData(TypedDict):
    title: str
    artist: str
    thumbnail: str


class TrackInfo(TypedDict):
    meta: MetaData
    source: str
    track_url: str
    artist_url: str


@dataclass(slots=True, frozen=True)
class Track:
    src_url: str

    src: discord.FFmpegOpusAudio
    title: str
    artist: str
    thumbnail: str
    track_url: str
    artist_url: str

    @classmethod
    async def from_dict(cls, data: TrackInfo) -> "Track":
        src_url = data["source"]
        src = await discord.FFmpegOpusAudio.from_probe(data["source"], **FFMPEG_OPTIONS)
        title = data["meta"]["title"]
        artist = data["meta"]["artist"]
        thumbnail = data["meta"]["thumbnail"]
        track_url = data["track_url"]
        artist_url = data["artist_url"]
        return cls(src_url, src, title, artist, thumbnail, track_url, artist_url)

    @classmethod
    async def from_track(cls, track: Optional["Track"]) -> Optional["Track"]:
        if isinstance(track, Track):
            src = await discord.FFmpegOpusAudio.from_probe(
                track.src_url, **FFMPEG_OPTIONS
            )
            return cls(
                track.src_url,
                src,
                track.title,
                track.artist,
                track.thumbnail,
                track.track_url,
                track.artist_url,
            )
        else:
            return None

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.src_url == other.src_url
        return False
    
    def __str__(self) -> str:
        return f"<red>{self.title}</> @ {self.artist}"