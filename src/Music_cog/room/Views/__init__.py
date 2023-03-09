from ABC import ViewABC
from Bot import TenB_Bot

from .MainView import MainView
from .SettingsView import SettingsView


def setup_view_client(client: TenB_Bot):
    ViewABC._client = client
