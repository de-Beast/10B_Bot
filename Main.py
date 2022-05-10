import Bot
from config import settings
from vk_api import get_api

# TODO:
# [x] Разбить код на файлы
# [x] Вместо фала использовать json или бд
# [x] Сделать кнопки рабочими
# [ ] Добавить отображение текущего трека
# [ ] Создать класс трека
# [ ] Создать класс очереди
# [ ] Создать собственный класс плеера
# [ ] Ставить плейлисты в очереди
# [ ] Мб решить проблему с капчами

if __name__ == "__main__":
    api = get_api(settings["vkadmin_token"])
    client = Bot.TenB_Bot()
    client.run(settings["token"])
