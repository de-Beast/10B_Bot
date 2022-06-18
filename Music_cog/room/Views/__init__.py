from discord.ext import bridge  # type: ignore

from abcs import ViewABC

from .MainView import MainView
from .SettingsView import SettingsView


def setup_view_client(client: bridge.Bot):
    ViewABC._client = client
