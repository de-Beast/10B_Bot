from . import music_player_cog
from . import music_room_cog
from .music_room_cog import get_music_room

def setup_music_cogs(client):
    music_player_cog.setup(client)
    music_room_cog.setup(client)