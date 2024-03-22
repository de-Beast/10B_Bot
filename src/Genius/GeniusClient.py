import lyricsgenius as lg  # type: ignore


class GeniusClient:
    __api: lg.Genius | None = None

    def __init__(self):
        self.song = None

    @property
    def api(self):
        if self.__api is None:
            self.__api = lg.Genius()
        return self.__api

    def get_song(self, title: str, author: str) -> None:
        self.song = self.api.search_song(title=title, artist=author)

    def get_thumbnail(self, title: str | None = None, author: str | None = None) -> str:
        if title is not None and author is not None:
            self.get_song(title, author)
        return self.song.song_art_image_thumbnail_url if self.song else None

    def get_lyrics(self, title: str | None = None, author: str | None = None) -> str:
        if title is not None and author is not None:
            self.get_song(title, author)
        return self.song.lyrics if self.song else None
