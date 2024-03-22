from re import fullmatch

from enums import SearchPlatform
from VK.VKAudioClient import VKAudioClient
from Youtube.YoutubeAudioClient import YoutubeAudioClient

from .Track import MetaData, TrackInfo


class DownloadMethodResolver:
    links_regex = {
        SearchPlatform.YOUTUBE: {
            "single": [
                r"https?://(?:www\.)?youtu(?:\.be|be\.com)/watch\?v=([a-zA-Z0-9+\-_]+)(&list=)?([a-zA-Z0-9+\-_]+)"
            ],
            "list": [
                r"https?://(?:www\.)?youtu(?:\.be|be\.com)/playlist\?list=([a-zA-Z0-9_\-]+)"
            ],
        },
        SearchPlatform.VK: {
            "single": [r"https?://(?:www\.)?vk\.com/audio(-?\d+_\d+)(?:_[0-9a-z]+)?"],
            "list": [
                r"https?://(?:www\.)?vk\.com/music/(?:playlist|album)/(-?\d+)_(\d+)_?([a-z0-9_]+)?",
                r"https?://(?:www\.)?vk\.com/audios\d+\?z=audio_playlist(-?\d+)_(\d+).+",
            ],
        },
    }

    def __init__(self, query: str, request_data: MetaData):
        self.query = query
        self.request_data = request_data

    def proccess_query(self) -> list[TrackInfo] | None:
        for platform, groups in self.links_regex.items():
            for group, patterns in groups.items():
                for pattern in patterns:
                    if result := fullmatch(pattern, self.query):
                        match platform:
                            case SearchPlatform.YOUTUBE:
                                yt_client = YoutubeAudioClient()
                                if group == "single":
                                    yt_track = yt_client.search(
                                        result[0], self.request_data
                                    )
                                    return [list(yt_track)[0]] if yt_track else None
                                elif group == "list":
                                    yt_tracks = yt_client.search(
                                        result[0], self.request_data, -1
                                    )
                                    return list(yt_tracks) if yt_tracks else None

                            case SearchPlatform.VK:
                                vk_client = VKAudioClient()
                                if group == "single":
                                    vk_track = vk_client.get_single(
                                        result[0], self.request_data
                                    )
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
                                        self.request_data,
                                    )
                                    return list(vk_tracks) if vk_tracks else None
                            case _:
                                match self.request_data["platform"]:
                                    case SearchPlatform.YOUTUBE:
                                        yt_client = YoutubeAudioClient()
                                        yt_tracks = yt_client.search(
                                            "ytsearch:" + self.query, self.request_data
                                        )
                                        return list(yt_tracks) if yt_tracks else None
                                    case SearchPlatform.VK:
                                        vk_client = VKAudioClient()
                                        vk_tracks = vk_client.search(
                                            self.query, self.request_data
                                        )
                                        return list(vk_tracks) if vk_tracks else None
        return None


async def define_stream_method(
    item: str, request_data: MetaData
) -> list[TrackInfo | None]:
    yt = fullmatch(
        r"https?://(?:www\.)?youtu(?:\.be|be\.com)/watch\?v=([a-zA-Z0-9+\-_]+)(&list=)?([a-zA-Z0-9+\-_]+)",
        item,
    )
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
