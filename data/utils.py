import logging
from .redis_instance import __redis_room__, __redis_users__, room, redis_random_waiting, random_users
from utils.time import dateMSC

# rooms = {chat_id: {users: {user_id: {status_online: str, activity: bool, connected: datetime}}, created: datetime}}
# random_waiting = {num_meet: {users: {user_id: {ready: bool = False}}}, created: datetime}
# random_users = {user_id: {skip_users: [int], tolk_users: [int],"added_time": время_добавления, "message_id": id_сообщения_или_null, data_activity: datetime}}

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
                                'ready': False,
                            } for user_id in users_dict
                        },
                    'created': dateMSC
                    }
                }
            redis_random_waiting.redis_cashed(data=data, ex=None)
            return data
    
    def random_user_inf(users: dict):
        main_data = random_users.redis_data()
        for user_id, value in users.items():
            data = {
                user_id: {
                    "skip_users": value["skip_users"],
                    "tolk_users": value['tolk_users'],
                    'last_activity': dateMSC
                }
            }
            main_data[user_id] = data
        result = random_users.redis_cashed(main_data, ex=None)
        return result
        
    
