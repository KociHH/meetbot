from config import LOCAL_REDIS

broker_url = LOCAL_REDIS
result_backend = LOCAL_REDIS

task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'Europe/Moscow'
enable_utc = True

worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000
worker_max_memory_per_child = 150000


beat_schedule = {
    'cleanup-inactive-users': {
        'task': 'tasks.cleanup_inactive_users',
        'schedule': 3600.0
    },
    'update-statistics': {
        'task': 'data.celery.tasks.update_statistics',
        'schedule': 1800.0
    },
}