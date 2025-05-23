import logging
import random
from aiogram.enums import ParseMode
from aiogram import Bot
from config import BOT_TOKEN
from aiogram.client.default import DefaultBotProperties
from data.redis_instance import redis_random, redis_random_waiting, random_users

logger = logging.getLogger(__name__)
# random_users = {user_id: {skip_users: [int], tolk_users: [int],"added_time": время_добавления, "message_id": id_сообщения_или_null, data_activity: datetime}}
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

def random_search(base: str, len_data: int | None) -> tuple[int, int] | None:
    if base == redis_random and len_data is not None and len_data >= 2:
        data: dict = random_users.redis_data()
        users_data = list(data.keys())
        random.shuffle(users_data)

        for i in range(len(users_data) - 1):
            user1_id_str = users_data[i]
            user2_id_str = users_data[i+1]

            user1_id = int(user1_id_str)
            user2_id = int(user2_id_str)

            user1_data = data.get(user1_id_str, {})
            user2_data = data.get(user2_id_str, {})

            user1_skip = user1_data.get('skip_users', [])
            user1_tolk = user1_data.get('tolk_users', [])
            user2_skip = user2_data.get('skip_users', [])
            user2_tolk = user2_data.get('tolk_users', [])
            
            if user2_id not in user1_skip and \
               user2_id not in user1_tolk and \
               user1_id not in user2_skip and \
               user1_id not in user2_tolk:
                return user1_id, user2_id
        return None
    return None

def count_meetings() -> int:
    data = redis_random_waiting.redis_data()
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

    def changes_to_random_waiting(self, field: str | int, value):
        data = redis_random_waiting.redis_data()

        for room_id, room_info in data.items():
            users: dict = room_info.get('users', {})

            if self.user_id in users:
                users[self.user_id][field] = value
                redis_random_waiting.redis_cashed(data=data)

                return room_id, True, users
        return None, False, None

    def delete_meet(self, count_meet: int):
        data = redis_random_waiting.redis_data()
        data.pop(count_meet) if isinstance(data, dict) else logger.error(f'Не тот тип {type(data)}')
        redis_random_waiting.redis_cashed(data=data, ex=None)
        return data

    def delete_random_user(self):
        data = random_users.redis_data()
        data.pop(str(self.user_id), None)
        random_users.redis_cashed(data=data, ex=None)

    def changes_to_random_user(self):
        data = random_users.redis_data()
        skip_users = data[self.user_id].get('skip_users', [])
        tolk_users = data[self.user_id].get('tolk_users', [])
        return skip_users, tolk_users

    def search_random_partner(self):
        data = random_users.redis_data()
        if len(data) <= 1:
            return None
        
        available_partners = [p for p in data if p != self.user_id]
        if not available_partners:
            return None
        
        partner_id = random.choice(available_partners)
        return {
            "partner_id": partner_id,
            "user_id": self.user_id,
        } 