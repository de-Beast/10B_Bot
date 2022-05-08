from . import MusicPlayerCog, MusicRoomCog


def setup_music_cogs(client):
    MusicPlayerCog.setup(client)
    MusicRoomCog.setup(client)
