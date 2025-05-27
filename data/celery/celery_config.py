from config import LOCAL_REDIS

broker_url = LOCAL_REDIS
result_backend = LOCAL_REDIS

task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'Europe/Moscow'
enable_utc = True

# celery -A data.celery.celery_app worker -l info -P solo
# celery -A data.celery.celery_app beat -l info

worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000
worker_max_memory_per_child = 150000

path_tasks = 'data.celery.tasks.'
beat_schedule = {
    'update-statistics': {
        'task': path_tasks + 'update_statistics',
        'schedule': 1800.0
    },
    'monitor-search-users-party': {
        'task': path_tasks + 'monitor_search_users_party',
        'schedule': 10.0
    },
    'animate-search': {
        'task': path_tasks + 'animate_search',
        'schedule': 5.0
    }
}
