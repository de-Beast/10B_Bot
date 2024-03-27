from typing import Generator

import yt_dlp as ytdl  # type: ignore

from enums import SearchPlatform
from Music_cog.player.Track import MetaData, TrackInfo


class YoutubeAudioClient:
    YDL_OPTIONS = {
        "format": "bestaudio/best",
        "extractaudio": True,
        "noplaylist": False,
        "source_address": "0.0.0.0",
        "ignoreerrors": True,
    }

    def __init__(self, request_data: MetaData):
        self.request_data = request_data

    def _get_generator(
        self, audios: Generator[dict, None, None], amount: int
    ) -> Generator[TrackInfo, None, None]:
        for num, audio in enumerate(audios):
            if num == amount:
                break
            if audio is None:
                amount += 1
                continue
            yield self._create_track_info(audio)

    def _create_track_info(self, audio: dict) -> TrackInfo:
        with ytdl.YoutubeDL(self.YDL_OPTIONS) as ydl:
            result: dict = ydl.extract_info(audio["url"], download=False, process=True)
            return TrackInfo(
                {
                    "source": result["url"],
                    "meta": {
                        "title": result["title"],
                        "author": result["uploader"],
                        "thumbnail": result["thumbnail"],
                        "platform": SearchPlatform.YOUTUBE,
                        "requested_by": self.request_data["requested_by"],
                        "requested_at": self.request_data["requested_at"],
                    },
                    "track_url": result["webpage_url"],
                    "author_url": result["uploader_url"],
                }
            )

    def _search_raw(self, query: str) -> Generator[dict, None, None] | dict | None:
        with ytdl.YoutubeDL(self.YDL_OPTIONS) as ydl:
            results = ydl.extract_info(query, download=False, process=False)
            if results is None:
                return None

            results = results.get("entries", results)
            if isinstance(results, dict):
                return results
            elif isinstance(results, Generator):
                return results
            return None

    def search(
        self, query: str, amount: int = 1
    ) -> Generator[TrackInfo, None, None] | TrackInfo | None:
        results = self._search_raw(query)
        if isinstance(results, dict):
            return self._create_track_info(results)
        return self._get_generator(results, amount) if results else None
