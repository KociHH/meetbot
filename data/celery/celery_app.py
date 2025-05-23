import eventlet
eventlet.monkey_patch()

from celery import Celery
from data.celery.celery_config import *

celery_app = Celery(
    'meetbot',
    broker=broker_url,
    backend=result_backend,
    include=['data.celery.tasks']
)

celery_app.config_from_object('data.celery.celery_config') 