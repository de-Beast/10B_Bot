from dotenv import dotenv_values

from src.enums import Configuration


def get_config(configuration: str = "prod") -> dict[str, str]:
    if "config" not in globals():
        globals()["config"] = {**dotenv_values(".env")}
        config: dict = globals()["config"]

        conf = Configuration.get_key(configuration)
        match conf:
            case Configuration.DEV:
                config.update(DISCORD_TOKEN=config.pop("DISCORD_TOKEN-dev"))
                config["CONFIGURATION"] = Configuration.DEV
                config["PREFIX"] = "++"
                config["ROOM_NAME"] = "10B-DEV_room"

            case Configuration.PROD:
                config.pop("DISCORD_TOKEN-dev")
                config["CONFIGURATION"] = Configuration.PROD
                config["PREFIX"] = "++"
                config["ROOM_NAME"] = "10B-classroom"

    return globals()["config"].copy()
