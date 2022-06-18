from abcs import MusicCogABC

from . import MusicPlayerCog, MusicRoomCog, MusicThreadCog


def setup_music_cogs(client):
    MusicCogABC._client = client
    MusicPlayerCog.setup(client)
    MusicRoomCog.setup(client)
    MusicThreadCog.setup(client)
