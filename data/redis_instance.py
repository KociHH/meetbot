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

def cheking_keys():
    for key, rb in keys.items():
        if not redis_base.exists(key):
            data = {}
            if key == redis_random:
                data = {
                    12345678: {
                        "exception": [],
                        'message_id': None,
                        'continue_id': None,
                        "last_animation_text": None,
                        "online_searching": False,
                        "message_count": 0,

                        'added_time': None,
                        'data_activity': None
                    }
                }
            if key == redis_random_waiting:
                data = {
                    1: {
                        "users": {
                            54321: {
                                'ready': False,
                                'message_id': None,
                            },
                            12345: {
                                'ready': False,
                                'message_id': None,
                            }
                        },
                        'created': None
                    }
                }
            rb.cached(data=data, key=key, ex=1200)
            logger.info(f'Создан {key} ключ в redis c датой: {data}')
            logger.info(f'Получненные данные {key}: {type(rb.get_cached())}')
