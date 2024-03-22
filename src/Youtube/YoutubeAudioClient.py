from typing import Generator

import yt_dlp as ytdl  # type: ignore

from Music_cog.player.Track import MetaData, TrackInfo


class YoutubeAudioClient:
    YDL_OPTIONS = {
        "format": "bestaudio/best",
        "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "extractaudio": True,
        "noplaylist": False,
        "writethumbnails": True,
        "source_address": "0.0.0.0",
        "nocheckcertificate": True,
    }

    def _search_raw(self, query: str) -> list[dict] | None:
        with ytdl.YoutubeDL(self.YDL_OPTIONS) as ydl:
            results: dict = ydl.extract_info(query, download=False)
            results = results.get("entries", results)
            if isinstance(results, list) and len(results) > 0:
                return results
            return None

    def search(
        self, query: str, request_data: MetaData, amount: int = 1
    ) -> Generator[TrackInfo, None, None] | None:
        results = self._search_raw(query)
        if results is None or len(results) == 0:
            return None
        for num, result in enumerate(results):
            if num == amount:
                break
            yield TrackInfo(
                {
                    "source": result["formats"][0]["url"],
                    "meta": {
                        "title": result["title"],
                        "author": result["uploader"],
                        "thumbnail": result["thumbnails"][-1]["url"],
                        "platform": request_data["platform"],
                        "requested_by": request_data["requested_by"],
                        "requested_at": request_data["requested_at"],
                    },
                    "track_url": result["webpage_url"],
                    "author_url": result["uploader_url"],
                }
            )
        return None
