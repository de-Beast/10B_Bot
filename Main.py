import sys
from typing import TYPE_CHECKING
from loguru import logger


from src.Bot import TenB_Bot

if TYPE_CHECKING:
    from src.vk_api import Api

# TODO:
# [x] Разбить код на файлы
# [x] Вместо фала использовать бд
# [x] Сделать кнопки рабочими
# [x] Добавить отображение текущего трека
# [x] Создать класс трека
# [x] Переделать бота commands.Bot в bridge.Bot
# [x] Создать класс очереди
# [x] Создать собственный класс плеера
# [ ] Ставить плейлисты в очереди
# [ ] Мб решить проблему с капчами


@logger.catch
def main(discord_token: str | None):
    client = TenB_Bot()
    client.run(discord_token)


if __name__ == "__main__":
    from config import get_config
    from src.vk_api import get_api

    config: dict = get_config(sys.argv[1])
    api: "Api" = get_api(config.get("VKADMIN_TOKEN"))
    main(config.get("DISCORD_TOKEN"))
