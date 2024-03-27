from . import MusicPlayerCog, MusicRoomCog, MusicThreadCog


def setup_audio_cogs(client):
    MusicPlayerCog.setup(client)
    MusicRoomCog.setup(client)
    MusicThreadCog.setup(client)
