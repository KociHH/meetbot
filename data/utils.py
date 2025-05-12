import logging
from .redis_instance import __redis_room__, __redis_users__
from utils.time import dateMSC

# {chat_id: {users: {user_id: {status_online: str, activity: bool, connected: datetime}}, created: datetime}}

logger = logging.getLogger(__name__)

class CreatingJson:
    def rooms(chat_id: int, users: list = None):
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
                    'created': dateMSC
                }
            }
            __redis_room__.cached(data=data)
            return data
    
