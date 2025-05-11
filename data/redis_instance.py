from kos_Htools.redis_core.redisetup import RedisBase
from redis import Redis

redis_data = Redis()

__redis_users__ = RedisBase(key='active_users', data=list, redis=redis_data)
__redis_room__ = RedisBase(key='rooms', data=dict, redis=redis_data) 