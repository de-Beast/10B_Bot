import os
from typing import TYPE_CHECKING
import dotenv
from loguru import logger

import Bot
from vk_api import get_api

if TYPE_CHECKING:
    from vk_api import Api

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
    client = Bot.TenB_Bot()
    client.run(discord_token)


if __name__ == "__main__":
    dotenv.load_dotenv()
    api: "Api" = get_api(os.getenv("VKADMIN_TOKEN"))
    main(os.getenv("DISCORD_TOKEN"))
