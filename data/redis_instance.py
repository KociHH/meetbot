from kos_Htools.redis_core.redisetup import RedisBase
from redis import Redis
import logging

logger = logging.getLogger(__name__)

redis_base = Redis()

redis_users = 'redis_users'
redis_random = 'redis_random'
redis_room = 'redis_room'
redis_random_waiting = 'redis_random_waiting'

# random
__redis_random_waiting__ = RedisBase(key=redis_random_waiting, data=dict, redis=redis_base)
__redis_random__ = RedisBase(key=redis_random, data=dict, redis=redis_base)

# rooms party
__redis_users__ = RedisBase(key=redis_users, data=list, redis=redis_base)
__redis_room__ = RedisBase(key=redis_room, data=dict, redis=redis_base)

users_pack = [
    redis_random,
    redis_users
]

class RAccess:
    def __init__(self, key: str) -> None:
        self.key = key
        self.obj = None
        
        if self.key == redis_room:
            self.obj = __redis_room__
        elif self.key == redis_users:
            self.obj = __redis_users__
        elif self.key == redis_random:
            self.obj = __redis_random__
        elif self.key == redis_random_waiting:
            self.obj = __redis_random_waiting__
        else:
            logger.error(f'Такого {self.key} нет в redis ключах')

    def redis_cashed(self, data: list | dict, ex: int | None = None):
        return self.obj.cashed(self.key, data, ex)
    
    def redis_data(self):
        return self.obj.get_cached(self.key)

    def search_online(self) -> int | bool:
        if isinstance(self.redis_data(), list) and self.key in users_pack:
            return len(self.redis_data())
        logger.error(f'Неправильный тип ключа: {type(self.redis_data())}')
        return False

users = RAccess(redis_users)
random_users = RAccess(redis_random)
room = RAccess(redis_room)
redis_random_waiting = RAccess(redis_random_waiting)