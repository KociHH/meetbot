import logging
import time
from .redis_instance import __redis_room__, __redis_users__, redis_room, redis_random_waiting, redis_random, __redis_random__, __redis_random_waiting__, redis_users
from utils.time import dateMSC, time_for_redis
from kos_Htools.telethon_core import multi

logger = logging.getLogger(__name__)

class CreatingJson:
    def __init__(self) -> None:
        pass

    def rooms(self, invite_link: str, chat_id: int, users: list = None):
            data = {
                chat_id: {
                    'users': {
                        user_id: {
                            'status_online': None,
                            'activity': None,
                            'connected': None,
                            'last_message': None,
                        } for user_id in users
                    },
                    'created': time_for_redis,
                    'invite_link': invite_link
                }
            }
            __redis_room__.cashed(redis_room, data=data, ex=None)
            return data
    
    def random_waiting(self, users: list, num_meet: int):
            data: dict = __redis_random_waiting__.get_cached()
            if len(users) != 2:
                logger.error(f'[Ошибка] юзеров != 2 человека: {users}')
                return None

            data[num_meet] = {
                      'users': {
                            user_id: {
                                'ready': False,
                                'message_id': None
                            } for user_id in users
                        },
                    'created': time_for_redis
                    }
            __redis_random_waiting__.cached(data=data, ex=None)
            return data
        
    def redis_data_user(self, users: list, base: str = redis_random, value: dict | None = None, main_data: dict | None = None) -> dict:
        if not main_data:
            main_data: dict = __redis_random__.get_cached() if base == redis_random else __redis_users__.get_cached()
        value = value if value is not None else {}
        
        for user_id in users:
            user_id_str = str(user_id)
            user_data: dict = main_data.get(user_id_str, {})

            exception = value.get('exception', user_data.get('exception', [])) 

            last_animation_text = value.get('last_animation_text', user_data.get('last_animation_text', None))
            message_id = value.get('message_id', user_data.get('message_id', None))
            continue_id = value.get('continue_id', user_data.get('continue_id', None))

            message_count = value.get('message_count', user_data.get('message_count', 0))
            online_searching = value.get('online_searching', user_data.get('online_searching', False))

            added_time = value.get('added_time', user_data.get('added_time', time.time()))
            data_activity = value.get('data_activity', user_data.get('data_activity', time_for_redis))

            # party
            if base == redis_random:
                main_data[user_id_str] = {
                    # exceptions
                    "exception": exception,
                    # messages
                    'message_id': message_id,
                    'continue_id': continue_id,
                    'last_animation_text': last_animation_text,
                    'message_count': int(message_count),
                    # time
                    'added_time': added_time,
                    'data_activity': data_activity,
                    'online_searching': online_searching
                }
                __redis_random__.cached(data=main_data, ex=None)
            
            # many
            elif base == redis_users:
                main_data[user_id_str] = {
                    # exceptions
                    "exception": exception,
                    # messages
                    'message_id': message_id,
                    'continue_id': continue_id,
                    'last_animation_text': last_animation_text,
                    'message_count': int(message_count),
                    # time
                    'added_time': added_time,
                    'data_activity': data_activity,
                    'online_searching': online_searching
                }
                __redis_users__.cached(data=main_data, ex=None)
        
        return main_data
    
    async def many_data_rooms(self, added_users: list[int], chat_id: list[int] | int, data: dict = None):
        if not data:
            data: dict = __redis_room__.get_cached()

        try:
            if chat_id:
                chat = data[chat_id]
                last_activity = chat.get('last_activity', time_for_redis)
                users_room: list = chat.get('users', [])
                if not users_room:
                    for uid in added_users:
                        users_room.append(uid)

                data[chat_id] = {
                    'last_activity': last_activity,
                    'users': users_room,
                }
                __redis_room__.cached(data=data, ex=None)
                return data
        
        except Exception as e:
            logger.error(f'Ошибка в many_data_rooms:\n {e}')
            return