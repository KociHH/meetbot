from celery import Celery
from data.celery.celery_config import *

celery_app = Celery(
    'meetbot',
    broker=broker_url,
    backend=result_backend,
    include=['tasks']
)

celery_app.config_from_object('celery_config') 