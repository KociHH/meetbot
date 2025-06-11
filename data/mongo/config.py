import pymongo

from config import MONGO_DB_URL

client = pymongo.MongoClient(MONGO_DB_URL)

redis_inactive_users_db = client['redis_users_db']

party_searchers = redis_inactive_users_db['party_searchers']
many_searchers = redis_inactive_users_db['many_searchers']

