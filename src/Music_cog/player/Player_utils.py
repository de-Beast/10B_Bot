from re import fullmatch
from time import sleep
from typing import Generator

import yt_dlp as ytdl  # type: ignore
from loguru import logger

from enums import SearchPlatform
from vk_api import get_api

from .Track import MetaData, TrackInfo

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "extractaudio": True,
    "noplaylist": False,
    "writethumbnails": True,
    "source_address": "0.0.0.0",
    "nocheckcertificate": True,
}


def search_yt_single(search_method: str, request_data: MetaData) -> TrackInfo | None:
    logger.info("single yt")
    with ytdl.YoutubeDL(YDL_OPTIONS) as ydl:
        infos: dict = ydl.extract_info(search_method, download=False)
        info = infos.get("entries", infos)
        if isinstance(info, list):
            if len(info) > 0:
                info = info[0]
            else:
                info = None

    return (
        TrackInfo(
            {
                "source": info["url"],
                "meta": {
                    "title": info["title"],
                    "author": info["uploader"],
                    "thumbnail": info["thumbnail"],
                    "platform": request_data["platform"],
                    "requested_by": request_data["requested_by"],
                    "requested_at": request_data["requested_at"],
                },
                "track_url": info["webpage_url"],
                "author_url": info["uploader_url"],
            }
        )
        if info
        else None
    )


def search_yt_list(search_method: str, request_data: MetaData) -> Generator[TrackInfo, None, None]:
    logger.info("playlist yt")
    with ytdl.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            infos = ydl.extract_info(search_method, download=False)["entries"]
        except Exception:
            info = ydl.extract_info(search_method, download=False)
    for info in infos:
        yield TrackInfo(
            {
                "source": info["formats"][0]["url"],
                "meta": {
                    "title": info["title"],
                    "author": info["uploader"],
                    "thumbnail": info["thumbnails"][-1]["url"],
                    "platform": request_data["platform"],
                    "requested_by": request_data["requested_by"],
                    "requested_at": request_data["requested_at"],
                },
                "track_url": info["webpage_url"],
                "author_url": info["uploader_url"],
            }
        )


def get_vk_album(owner_id: int, id: int, key: str | None, request_data: MetaData) -> Generator[TrackInfo | None, None, None]:
    logger.info("album vk")
    api = get_api()
    audios = api.method("audio.get", owner_id=owner_id, album_id=id, access_key=key)
    if audios["count"] == 0:
        yield None
    for aud in audios["items"]:
        a = get_vk_single(f"{aud['owner_id']}_{aud['id']}", request_data)
        if not a:
            print(a)
            sleep(10)
            continue
        yield a


def search_vk(name: str) -> str | None:
    api = get_api()
    audio = api.method("audio.search", q=name, auto_complete=1)
    if audio["count"] == 0:
        return None
    return f"{audio['items'][0]['owner_id']}_{audio['items'][0]['id']}"


def get_vk_single(id: str | None, request_data: MetaData) -> TrackInfo | None:
    logger.info("single vk")
    if not id:
        return None
    api = get_api()
    audio = api.method("audio.getById", audios=id)
    if len(audio) == 0:
        return None
    return TrackInfo(
        {
            "source": audio[0]["url"],
            "meta": {
                "title": audio[0]["title"],
                "author": audio[0]["author"],
                "thumbnail": audio[0]["album"]["thumb"]["photo_1200"] if "album" in audio[0] else None,
                "platform": request_data["platform"],
                "requested_by": request_data["requested_by"],
                "requested_at": request_data["requested_at"],
            },
            "track_url": audio[0]["url"],
            "author_url": audio[0]["url"],
        }
    )


async def define_stream_method(item: str, request_data: MetaData) -> list[TrackInfo | None]:
    yt = fullmatch(r"https?://(?:www\.)?youtu(?:\.be|be\.com)/watch\?v=([a-zA-Z0-9+\-_]+)(&list=)?([a-zA-Z0-9+\-_]+)", item)
    yt_list = fullmatch(
        r"https?://(?:www\.)?youtu(?:\.be|be\.com)/playlist\?list=([a-zA-Z0-9_\-]+)",
        item,
    )
    vk = fullmatch(r"https?://(?:www\.)?vk\.com/audio(-?\d+_\d+)(?:_[0-9a-z]+)?", item)
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
        return [search_yt_single(yt[0], request_data)]
    if yt_list:
        return list(search_yt_list(yt_list[0], request_data))
    if vk:
        return [get_vk_single(vk[1], request_data)]
    if vk_list:
        key: str | None = str(vk_list[3]) if len(vk_list.groups()) > 2 else None
        return list(get_vk_album(int(vk_list[1]), int(vk_list[2]), key, request_data))
    match request_data["platform"]:
        case SearchPlatform.YOUTUBE:
            return [search_yt_single("ytsearch:" + item, request_data)]
        case SearchPlatform.VK:
            return [get_vk_single(search_vk(item), request_data)]
    return [None]
