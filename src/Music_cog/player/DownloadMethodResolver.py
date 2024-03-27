from re import fullmatch
from typing import Generator

from enums import SearchPlatform
from VK.VKAudioClient import VKAudioClient
from Youtube.YoutubeAudioClient import YoutubeAudioClient

from .Track import MetaData, TrackInfo


class DownloadMethodResolver:
    links_regex = {
        SearchPlatform.YOUTUBE: {
            "single": [
                r"https?://(?:www\.)?youtu(?:\.be|be\.com)/watch\?v=([a-zA-Z0-9+\-_]+)(&list=)?([a-zA-Z0-9+\-_]+)?(&index=)?(\d+)?"
            ],
            "list": [
                r"https?://(?:www\.)?youtu(?:\.be|be\.com)/playlist\?list=([a-zA-Z0-9_\-]+)"
            ],
        },
        SearchPlatform.VK: {
            "single": [r"https?://(?:www\.)?vk\.com/audio(-?\d+_\d+)(?:_[0-9a-z]+)?"],
            "list": [
                r"https?://(?:www\.)?vk\.com/music/(?:playlist|album)/(-?\d+)_(\d+)_?([a-z0-9_]+)?",
                r"https?://(?:www\.)?vk\.com/.+z=audio_playlist(-?\d+)_(\d+)(.+)?",
            ],
        },
    }

    def __init__(self, query: str, request_data: MetaData):
        self.query = query
        self.request_data = request_data

    async def proccess_query(
        self,
    ) -> Generator[TrackInfo, None, None] | TrackInfo | None:
        for platform, groups in self.links_regex.items():
            for group, patterns in groups.items():
                for pattern in patterns:
                    if result := fullmatch(pattern, self.query):
                        match platform:
                            case SearchPlatform.YOUTUBE:
                                yt_client = YoutubeAudioClient(self.request_data)
                                if group == "single":
                                    tracks = yt_client.search(result[1])
                                    return tracks
                                elif group == "list":
                                    tracks = yt_client.search(result[0], -1)
                                    return tracks

                            case SearchPlatform.VK:
                                vk_client = VKAudioClient(self.request_data)
                                if group == "single":
                                    tracks = vk_client.get_single(result[1])
                                    return tracks
                                elif group == "list":
                                    key: str | None = (
                                        str(result[3])
                                        if len(result.groups()) > 2
                                        else None
                                    )
                                    tracks = vk_client.get_album(
                                        int(result[1]),
                                        int(result[2]),
                                        key,
                                    )
                                    return tracks
        match self.request_data["platform"]:
            case SearchPlatform.YOUTUBE:
                yt_client = YoutubeAudioClient(self.request_data)
                tracks = yt_client.search("ytsearch:" + self.query)
                return tracks
            case SearchPlatform.VK:
                vk_client = VKAudioClient(self.request_data)
                tracks = vk_client.search(self.query)
                return tracks

        raise Exception("Can't resolve query")
