import Bot

from config import settings
from vk_api import get_api

# TODO: 
# [ ] Разбить код на файлы
# [ ] Создать собственный класс плеера
# [ ] Вместо фала использовать json или бд
# [ ] Отображение очереди
# [ ] Ставить плейлисты в очереди
# [ ] Сделать кнопки рабочими
# [ ] Мб решить проблему с капчами

if __name__ == '__main__':
	api = get_api(settings['vkadmin_token'])
	client = Bot.TenB_Bot()
	client.run(settings['token'])
