from loguru import logger

import Bot
from config import settings
from vk_api import get_api

# TODO:
# [x] Разбить код на файлы
# [x] Вместо фала использовать json или бд
# [x] Сделать кнопки рабочими
# [x] Добавить отображение текущего трека
# [x] Создать класс трека
# [ ] Переделать бота commands.Bot в bridge.Bot
# [ ] Создать класс очереди
# [ ] Создать собственный класс плеера
# [ ] Ставить плейлисты в очереди
# [ ] Мб решить проблему с капчами


@logger.catch
def main(discord_token: str):
    client = Bot.TenB_Bot()
    client.run(discord_token)


if __name__ == "__main__":
    api = get_api(settings["vkadmin_token"])
    main(settings["discord_token"])
