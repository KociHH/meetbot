import logging
import random
from typing import Any
from aiogram.enums import ParseMode
from aiogram import Bot
from config import BOT_TOKEN
from aiogram.client.default import DefaultBotProperties
from data.redis_instance import redis_random, redis_random_waiting, __redis_random__, __redis_random_waiting__

logger = logging.getLogger(__name__)
# random_users = {user_id: {skip_users: [int], tolk_users: [int],"added_time": время_добавления, "message_id": id_сообщения_или_null, data_activity: datetime}}
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

def random_search(users_data: list[str], data: dict) -> tuple[int, int] | None:
    size = len(users_data)
    if size < 2:
        return None

    random.shuffle(users_data)

    for i in range(size - 1):
        user1_id_str = users_data[i]
        user2_id_str = users_data[i+1]

        user1_data = data.get(user1_id_str, {})
        user2_data = data.get(user2_id_str, {})

        user1_id = int(user1_id_str)
        user2_id = int(user2_id_str)

        user1_exception = user1_data.get('exception', [])
        user2_exception = user2_data.get('exception', [])
        
        if user2_id not in user1_exception and \
           user1_id not in user2_exception:
            user1_exception.append(user2_id)
            user2_exception.append(user1_id)
            
            __redis_random__.cached(data=data, ex=None)
            return user1_id, user2_id
    
    logger.info(f'Нет подходящих юзеров для пар, в поиске: {size}')
    return None

def count_meetings() -> int:
    data = __redis_random_waiting__.get_cached(redis_random_waiting)
    if not data:
        return 1
    
    meetings = sorted(int(meet) for meet in data.keys())
    dynamic_count = 1

    for meet in meetings:
        if meet == dynamic_count:
            dynamic_count += 1
        else:
            break
    return dynamic_count

class RandomMeet:
    def __init__(self, user_id) -> None:
        self.user_id = user_id

    def getitem_to_random_user(self, item: str = None, change_to: str | int | None = None, _change_provided: bool = False, update_many: dict = None, data: dict | None = None):
        if not data:
            data: dict = __redis_random__.get_cached()
        if isinstance(self.user_id, int):
            self.user_id = str(self.user_id)
        
        if update_many:
            if self.user_id in data and isinstance(data.get(self.user_id), dict):
                user_data = data[self.user_id]
                for itm, val in update_many.items():
                    user_data[itm] = val
                __redis_random__.cached(data=data, ex=None)
                return data
            else:
                logger.error(f'Пользовательские данные не найдены или имеют неверный формат для {self.user_id} при попытке группового обновления.')
                return None       

        obj = data.get(self.user_id, {}).get(item, None)
        if self.user_id in data.keys():
            if _change_provided:
                if self.user_id in data and isinstance(data.get(self.user_id), dict):
                     data[self.user_id][item] = change_to
                     __redis_random__.cached(data=data, ex=None)
                else:
                     logger.error(f'Пользовательские данные не найдены или имеют неверный формат для {self.user_id} при попытке обновления {item}')
                return data.get(self.user_id, {}).get(item, None)
            else:
                if obj is not None:
                    return obj
                else:
                    logger.warning(f'Не найден объект: {item} |p.s {obj} для пользователя {self.user_id}')
                    return None

        else:
            logger.warning(f'Такого {self.user_id} нет в {redis_random}')
            return None

    def meeting_account(data: dict | None = None) -> int:
        if not data:
            data = __redis_random_waiting__.get_cached()
        rooms = sorted(data.keys())
        size = len(rooms)
        if size >= 1:
            for i in range(1, len(rooms)):
                if i not in rooms:
                    return i
        return 1

    def changes_to_random_waiting(self, field: str | int, value: Any | None = None):
        data = __redis_random_waiting__.get_cached()

        for room_id, room_info in data.items():
            users: dict = room_info.get('users', {})

            if self.user_id in users:
                users[self.user_id][field] = value
                __redis_random_waiting__.cached(data=data, ex=None)

                return room_id, True, users
        return None, False, None

    def delete_meet(count_meet: int):
        data = __redis_random_waiting__.get_cached(redis_random_waiting)
        data.pop(count_meet) if isinstance(data, dict) else logger.error(f'Не тот тип {type(data)}')
        __redis_random_waiting__.cached(data=data, ex=None)
        return data

    def delete_random_user(self):
        data = __redis_random__.get_cached(redis_random)
        data.pop(str(self.user_id), None)
        __redis_random__.cached(data=data, ex=None)