from . import SpeechToTextCog


def setup_audio_cogs(client):
    SpeechToTextCog.setup(client)