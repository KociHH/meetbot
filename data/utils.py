import logging
from .redis_instance import __redis_room__, __redis_users__, room, redis_random_waiting
from utils.time import dateMSC

# {chat_id: {users: {user_id: {status_online: str, activity: bool, connected: datetime}}, created: datetime}}
# {num_meet: {users: {user_id: {skip_users: [int], tolk_users: [int], ready: bool = False}}}, created: datetime}

logger = logging.getLogger(__name__)

class CreatingJson:
    def rooms(invite_link: str, chat_id: int, users: list = None):
            data = {
                chat_id: {
                    'users': {
                        user_id: {
                            'status_online': 'Undefind',
                            'activity': None,
                            'connected': None,
                            'last_message': None,
                        } for user_id in users
                    },
                    'created': dateMSC,
                    'invite_link': invite_link
                }
            }
            room.redis_cashed(data=data, ex=None)
            return data
    
    def random_waiting(users: dict[int, dict[str, int]], num_meet: int = 1):
            users_dict = users.get('users', {})
            size_users = len(users_dict)
            if size_users != 2:
                logger.error(f'[Ошибка] юзеров != 2 человека: {size_users}\n Словарь: {users}')
                return False

            data = {
                num_meet: {
                      'users': {
                            user_id: {
                                'skip_users': users_dict[user_id]['skip_users'],
                                'go_talk': users_dict[user_id]['tolk_users'],
                                'ready': False,
                            } for user_id in users_dict
                        },
                    'created': dateMSC
                    }
                }
            redis_random_waiting.redis_cashed(data=data, ex=None)
            return data
    
