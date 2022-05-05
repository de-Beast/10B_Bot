from . import MusicPlayerCog
from . import MusicRoomCog

def setup_music_cogs(client):
    MusicPlayerCog.setup(client)
    MusicRoomCog.setup(client)