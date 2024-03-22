from typing import Generator

from Music_cog.player.Track import MetaData, TrackInfo

from .VKAPI import VKAPI


class VKAudioClient:
    __api: VKAPI | None = None

    @property
    def api(self) -> VKAPI:
        if self.__api is None:
            self.__api = VKAPI()
        return self.__api

    def _get_single_raw(self, id: str | None) -> dict:
        return self.api.method("audio.getById", audios=id)[0]

    def _get_album_raw(self, owner_id: int, id: int, key: str | None) -> dict:
        return self.api.method(
            "audio.get", owner_id=owner_id, album_id=id, access_key=key
        )

    def _search_raw(self, query: str) -> dict:
        return self.api.method("audio.search", q=query, auto_complete=1)

    def get_single(self, id: str | None, request_data: MetaData) -> TrackInfo | None:
        audio = self._get_single_raw(id)
        if len(audio) == 0:
            return None
        return TrackInfo(
            {
                "source": audio["url"],
                "meta": {
                    "title": audio["title"],
                    "author": audio["artist"],
                    "thumbnail": audio["album"]["thumb"]["photo_1200"]
                    if "album" in audio
                    else "",
                    "platform": request_data["platform"],
                    "requested_by": request_data["requested_by"],
                    "requested_at": request_data["requested_at"],
                },
                "track_url": audio["url"],
                "author_url": audio["url"],
            }
        )

    def get_album(
        self, owner_id: int, id: int, key: str | None, request_data: MetaData
    ) -> Generator[TrackInfo, None, None] | None:
        audios = self._get_album_raw(owner_id, id, key)
        if audios["count"] == 0:
            return None
        for audio in audios["items"]:
            result = self.get_single(f"{audio['owner_id']}_{audio['id']}", request_data)
            if not result:
                continue
            yield result
        return None

    def search(
        self, query: str, request_data: MetaData, amount: int = 1
    ) -> Generator[TrackInfo, None, None] | None:
        audios = self._search_raw(query)
        if audios["count"] == 0:
            return None
        for num, audio in enumerate(audios["items"]):
            if num == amount:
                break
            result = self.get_single(
                f"{audio[num]['owner_id']}_{audio[num]['id']}", request_data
            )
            if not result:
                continue
            yield result
        return None
