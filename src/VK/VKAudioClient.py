from typing import Generator

from enums import SearchPlatform
from Genius import GeniusClient
from Music_cog.player.Track import MetaData, TrackInfo

from .VKAPI import VKAPI


class VKAudioClient:
    __api: VKAPI | None = None

    def __init__(self, request_data: MetaData):
        self.request_data = request_data
    
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
    
    def _create_track_info(self, audio_info: dict) -> TrackInfo:
        return TrackInfo(
            {
                "source": audio_info["url"],
                "meta": {
                    "title": audio_info["title"],
                    "author": audio_info["artist"],
                    "thumbnail": audio_info["album"]["thumb"]["photo_1200"]
                    if "album" in audio_info
                    else GeniusClient().get_thumbnail(title=audio_info["title"], author=audio_info["artist"]),
                    "platform": SearchPlatform.VK,
                    "requested_by": self.request_data["requested_by"],
                    "requested_at": self.request_data["requested_at"],
                },
                "track_url": f"https://vk.com/audio{audio_info['release_audio_id']}" 
                            if 'release_audio_id' in audio_info else audio_info["url"],
                "author_url": f"https://vk.com/artist/{audio_info['main_artists'][0]['id']}"
                            if 'main_artists' in audio_info else audio_info["url"],
            }
        )

    def _get_generator(self, audios: dict, amount: int) -> Generator[TrackInfo, None, None]:
        for num, audio in enumerate(audios["items"]):
            if num == amount:
                break
            if audio['is_licensed'] is False or audio['url'] == '':
                continue
            yield self._create_track_info(audio)
    
    def get_single(self, id: str | None) -> TrackInfo | None:
        audio = self._get_single_raw(id)
        return self._create_track_info(audio) if audio else None

    def get_album(
        self, owner_id: int, id: int, key: str | None
    ) -> Generator[TrackInfo, None, None] | None:
        audios = self._get_album_raw(owner_id, id, key)
        return self._get_generator(audios, -1) if audios["count"] > 0 else None

    def search(
        self, query: str, amount: int = 1
    ) -> Generator[TrackInfo, None, None] | None:
        audios = self._search_raw(query)
        return self._get_generator(audios, amount) if audios["count"] > 0 else None
