import sys

from loguru import logger

from Bot import TenB_Bot


@logger.catch
def main(discord_token: str | None):
    client = TenB_Bot()
    client.run(discord_token)


if __name__ == "__main__":
    from config import get_config

    config = get_config(sys.argv[1] if len(sys.argv) > 1 else None)
    main(config.get("DISCORD_TOKEN"))
