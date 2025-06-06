import os
from typing import Any

import dotenv

from enums import Configuration


def get_config(configuration: str | None = None) -> dict[str, Any]:
    if configuration is None:
        configuration = "prod"

    if "config" not in globals():
        globals()["config"] = {}
        config: dict = globals()["config"]

        conf = Configuration.get_key(configuration)
        match conf:
            case Configuration.DEV:
                config["CONFIGURATION"] = Configuration.DEV
                config["DISCORD_TOKEN"] = os.getenv("DISCORD_TOKEN-dev")
                config["PREFIX"] = "++"
                config["ROOM_NAME"] = "10B-DEV_room"

            case Configuration.PROD:
                config["CONFIGURATION"] = Configuration.PROD
                config["DISCORD_TOKEN"] = os.getenv("DISCORD_TOKEN")
                config["PREFIX"] = "++"
                config["ROOM_NAME"] = "10B-classroom"

        config["VKADMIN_TOKEN"] = os.getenv("VKADMIN_TOKEN")
        config["MONGODB_URL"] = os.getenv("MONGODB_URL")

    return globals()["config"].copy()


if __name__ == "config":
    dotenv.load_dotenv(dotenv.find_dotenv())
