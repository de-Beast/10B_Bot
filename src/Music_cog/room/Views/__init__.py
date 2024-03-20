from ABC import ViewABC
from Bot import TenB_Bot

from .PlayerView import PlayerView
from .SettingsView import SettingsView


def setup_view_client(client: TenB_Bot):
    ViewABC._client = client
