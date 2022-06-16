from re import fullmatch
from time import sleep
from typing import Generator, Optional

import youtube_dl  # type: ignore
from loguru import logger

from enums import SearchPlatform
from vk_api import get_api

from .Track import TrackInfo

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "extractaudio": True,
    "noplaylist": False,
    "writethumbnails": True,
    "source_address": "0.0.0.0",
    "nocheckcertificate": True,
}


def search_yt_single(search_method: str) -> TrackInfo:
    logger.info("single yt")
    with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(search_method, download=False)["entries"][0]
        except Exception:
            info = ydl.extract_info(search_method, download=False)
    return TrackInfo({
        "source": info["formats"][0]["url"],
        "meta": {
            "title": info["title"],
            "artist": info["uploader"],
            "thumbnail": info["thumbnails"][-1]["url"],
        },
        "track_url": info["webpage_url"],
        "artist_url": info["uploader_url"],
    })


def search_yt_list(search_method: str) -> Generator[TrackInfo, None, None]:
    logger.info("playlist yt")
    with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            infos = ydl.extract_info(search_method, download=False)["entries"]
        except Exception:
            info = ydl.extract_info(search_method, download=False)
    for info in infos:
        yield TrackInfo({
            "source": info["formats"][0]["url"],
            "meta": {
                "title": info["title"],
                "artist": info["uploader"],
                "thumbnail": info["thumbnails"][-1]["url"],
            },
            "track_url": info["webpage_url"],
            "artist_url": info["uploader_url"],
        })


def get_vk_album(owner_id: int, id: int, key) -> Generator[Optional[TrackInfo], None, None]:
    logger.info("album vk")
    api = get_api()
    audios = api.method("audio.get", owner_id=owner_id, album_id=id, access_key=key)
    if audios["count"] == 0:
        yield None
    for aud in audios["items"]:
        a = get_vk_single(f"{aud['owner_id']}_{aud['id']}")
        if not a:
            print(a)
            sleep(10)
            continue
        yield a


def search_vk(name: str) -> Optional[str]:
    api = get_api()
    audio = api.method("audio.search", q=name, auto_complete=1)
    if audio["count"] == 0:
        return None
    return f"{audio['items'][0]['owner_id']}_{audio['items'][0]['id']}"


def get_vk_single(id: Optional[str]) -> Optional[TrackInfo]:
    logger.info("single vk")
    if not id:
        return None
    api = get_api()
    audio = api.method("audio.getById", audios=id)
    if len(audio) == 0:
        return None
    return TrackInfo({
        "source": audio[0]["url"],
        "meta": {
            "title": audio[0]["title"],
            "artist": audio[0]["artist"],
            "thumbnail": audio[0]["album"]["thumb"]["photo_1200"]
            if audio[0]["album"]
            else None,
        },
        "track_url": audio[0]["url"],
        "artist_url": audio[0]["url"],
    })


async def define_stream_method(item: str, search_platform: SearchPlatform) -> list[Optional[TrackInfo]]:
    yt = fullmatch(
        r"https?://(?:www\.)?youtu(?:\.be|be\.com)/watch\?v=([a-zA-Z0-9]+)", item
    )
    yt_list = fullmatch(
        r"https?://(?:www\.)?youtu(?:\.be|be\.com)/playlist\?list=([a-zA-Z0-9_\-]+)",
        item,
    )
    vk = fullmatch(r"https?://(?:www\.)?vk\.com/audio(-?\d+_\d+)(?:_\d+)?", item)
    vk_list = fullmatch(
        r"https?://(?:www\.)?vk\.com/music/(?:playlist|album)/(-?\d+)_(\d+)_?([a-z0-9_]+)?",
        item,
    )
    if not vk_list:
        vk_list = fullmatch(
            r"https?://(?:www\.)?vk\.com/audios\d+\?z=audio_playlist(-?\d+)_(\d+).+",
            item,
        )
    if yt:
        return [search_yt_single(yt[0])]
    if yt_list:
        return list(search_yt_list(yt_list[0]))
    if vk:
        return [get_vk_single(vk[1])]
    if vk_list:
        key = vk_list[3] if len(vk_list.groups()) > 2 else None
        return list(get_vk_album(vk_list[1], vk_list[2], key))  # type: ignore
    match search_platform:
        case SearchPlatform.YOUTUBE:
            return [search_yt_single("ytsearch:" + item)]
        case SearchPlatform.VK:
            return [get_vk_single(search_vk(item))]
    return [None]
