from re import fullmatch

from enums import SearchPlatform
from VK.VKAudioClient import VKAudioClient
from Youtube.YoutubeAudioClient import YoutubeAudioClient

from .Track import MetaData, TrackInfo

# TODO: Добавить обработку долгих загрузок плейлистов

class DownloadMethodResolver:
    links_regex = {
        SearchPlatform.YOUTUBE: {
            "single": [
                r"https?://(?:www\.)?youtu(?:\.be|be\.com)/watch\?v=([a-zA-Z0-9+\-_]+)(&list=)?([a-zA-Z0-9+\-_]+)?"
            ],
            "list": [
                r"https?://(?:www\.)?youtu(?:\.be|be\.com)/playlist\?list=([a-zA-Z0-9_\-]+)"
            ],
        },
        SearchPlatform.VK: {
            "single": [r"https?://(?:www\.)?vk\.com/audio(-?\d+_\d+)(?:_[0-9a-z]+)?"],
            "list": [
                r"https?://(?:www\.)?vk\.com/music/(?:playlist|album)/(-?\d+)_(\d+)_?([a-z0-9_]+)?",
                r"https?://(?:www\.)?vk\.com/audios.+z=audio_playlist(-?\d+)_(\d+)(.+)?",
            ],
        },
    }

    def __init__(self, query: str, request_data: MetaData):
        self.query = query
        self.request_data = request_data

    async def proccess_query(self) -> list[TrackInfo] | None:
        for platform, groups in self.links_regex.items():
            for group, patterns in groups.items():
                for pattern in patterns:
                    if result := fullmatch(pattern, self.query):
                        match platform:
                            case SearchPlatform.YOUTUBE:
                                yt_client = YoutubeAudioClient(self.request_data)
                                if group == "single":
                                    yt_track = yt_client.search(result[0])
                                    return [list(yt_track)[0]] if yt_track else None
                                elif group == "list":
                                    yt_tracks = yt_client.search(result[0], -1)
                                    return list(yt_tracks) if yt_tracks else None

                            case SearchPlatform.VK:
                                vk_client = VKAudioClient(self.request_data)
                                if group == "single":
                                    vk_track = vk_client.get_single(result[1])
                                    return [vk_track] if vk_track else None
                                elif group == "list":
                                    key: str | None = (
                                        str(result[3])
                                        if len(result.groups()) > 2
                                        else None
                                    )
                                    vk_tracks = vk_client.get_album(
                                        int(result[1]),
                                        int(result[2]),
                                        key,
                                    )
                                    return list(vk_tracks) if vk_tracks else None
        match self.request_data["platform"]:
            case SearchPlatform.YOUTUBE:
                yt_client = YoutubeAudioClient(self.request_data)
                yt_tracks = yt_client.search("ytsearch:" + self.query)
                return list(yt_tracks) if yt_tracks else None
            case SearchPlatform.VK:
                vk_client = VKAudioClient(self.request_data)
                vk_tracks = vk_client.search(self.query)
                return list(vk_tracks) if vk_tracks else None

        raise Exception("Can't resolve query")
