from kos_Htools.redis_core.redisetup import RedisBase
from redis import Redis
import logging

logger = logging.getLogger(__name__)

redis_base = Redis()

__redis_users__ = RedisBase(key='active_users', data=list, redis=redis_base)
__redis_room__ = RedisBase(key='rooms', data=dict, redis=redis_base)

def redis_data(key: str):
    if key == 'active_users':
        data = __redis_users__.get_cached(key)
    
    elif key == 'rooms':
        data = __redis_room__.get_cached(key)
    
    else:
        logger.error(f'{key} такого ключа нет в redis данных.')
        return None

    return data