from kos_Htools.redis_core.redisetup import RedisBase
from redis import Redis
import logging

from config import ADMIN_ID

logger = logging.getLogger(__name__)

redis_base = Redis()

redis_users = 'searching_party'
redis_room = 'redis_room'

redis_random = 'searching_patners'
redis_random_waiting = 'waiting_random'

# random patners
__redis_random_waiting__ = RedisBase(key=redis_random_waiting, data={}, redis=redis_base)
__redis_random__ = RedisBase(key=redis_random, data={}, redis=redis_base)

# rooms party
__redis_users__ = RedisBase(key=redis_users, data={}, redis=redis_base)
__redis_room__ = RedisBase(key=redis_room, data={}, redis=redis_base)

keys = {
   redis_random_waiting: __redis_random_waiting__, 
   redis_random: __redis_random__,
   redis_users: __redis_users__,
   redis_room: __redis_room__
}

# rooms = {chat_id: {users: {user_id: {status_online: str, activity: bool, connected: datetime}}, created: datetime}}
# random_waiting = {num_meet: {users: {user_id: {ready: bool = False}}}, created: datetime}
# random_users = {user_id: {skip_users: [int], tolk_users: [int],"added_time": время_добавления, "message_id": id_сообщения_или_null, data_activity: datetime}}

def cheking_keys():
    for key, rb in keys.items():
        if not redis_base.exists(key):
            if key == redis_random or redis_users:
                data = {
                    ADMIN_ID[0]: {
                    "skip_users": [],
                    "tolk_users": [],

                    'message_id': None,
                    'continue_id': None,
                    "last_animation_text": None,
                    "message_count": 0,

                    'added_time': None,
                    'data_activity': None
                    }
                }
            rb.cached(data=data, key=key, ex=1200)
            logger.info(f'Создан {key} ключ в redis c датой: {data}')
            logger.info(f'Получненные данные {key}: {type(rb.get_cached())}')
