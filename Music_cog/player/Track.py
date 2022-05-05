import discord


FFMPEG_OPTIONS = {
			'before_options': ' \
				-reconnect 1 \
				-reconnect_streamed 1 \
				-reconnect_at_eof 1 \
				-reconnect_on_network_error 1 \
				-reconnect_on_http_error 1 \
				-reconnect_delay_max 2',
			'options': '-vn'
		}

class Track():
    def __init__(self, src: discord.FFmpegOpusAudio,
                 title: str, author: str, thumbnail: str,
                 track_url: str, author_url: str):
        self.src = src

        self.track_url = track_url
        self.author_url = author_url

        self.title = title
        self.author = author
        self.thumbnail = thumbnail


    @classmethod
    async def from_dict(cls, data: dict):
        src = await discord.FFmpegOpusAudio.from_probe(data['source'], **FFMPEG_OPTIONS)
        title = data['meta'].get('title')
        author = data['meta'].get('author')
        thumbnail = data['meta'].get('thumbnail')
        track_url = data.get('track_url')
        author_url = data.get('author_url')
        return cls(src, title, author, thumbnail, track_url, author_url)
