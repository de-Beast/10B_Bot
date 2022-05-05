from . import MusicPlayerCog
from . import MusicRoomCog
from .MusicRoomCog import get_music_room

def setup_music_cogs(client):
    MusicPlayerCog.setup(client)
    MusicRoomCog.setup(client)
