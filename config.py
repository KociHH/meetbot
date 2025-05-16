import logging
from typing import Any
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)

load_dotenv()

def get_env_var(key: str, default: Any = None) -> Any:
    value = os.getenv(key.upper(), default)
    if value is None:
        logger.warning(f"Переменная окружения {key} не найдена!")
    return value

BOT_TOKEN = get_env_var('BOT_TOKEN')
API_ID = get_env_var('TELEGRAM_API_ID')
API_HASH = get_env_var('TELEGRAM_API_HASH')
PHONE_NUMBER = get_env_var('TELEGRAM_PHONE_NUMBER')
BD_URL_POSTGRES = get_env_var('BD_URL_POSTGRES')
WEB_HOOK_URL = get_env_var('WEB_HOOK_URL')
WEB_HOOK_HOST = get_env_var('WEB_HOOK_HOST')
WEB_HOOK_PORT = get_env_var('WEB_HOOK_PORT')
CHANNEL_ID = get_env_var('CHANNEL_ID')
ADMIN_ID = get_env_var('ADMIN_ID')
BOT_USERNAME = get_env_var('BOT_USERNAME')
BOT_ID = get_env_var('BOT_ID')

def loadenvr(key: str, default: Any = None) -> Any:
    key = key.upper()
    return globals().get(key, get_env_var(key, default))




