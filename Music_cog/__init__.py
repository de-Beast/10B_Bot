from abcs import MusicCogABC

from . import MusicPlayerCog, MusicRoomCog


def setup_music_cogs(client):
    MusicCogABC._client = client
    MusicPlayerCog.setup(client)
    MusicRoomCog.setup(client)
