import random
import re
import logging
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils import markdown
from keyboards.button_names import chats_bt
from keyboards.reply_button import chats
from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, BOT_USERNAME
from aiogram.enums import ParseMode
from .words_or_other import INVISIBLE_CHARS, kats

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

samples_log = '- - - - - - - - - - - - - - - - - - - - - - - - - - - - -'
group_title = "Комнатка"
about_groups = f"""
🫨 Группа специально создана для общения и нахождения новых знакомств.\n
Бот: @{BOT_USERNAME}
"""

hello_text = markdown.text(
    f'Привет\n'
    f'Этот бот предназначен для быстрых знакомств\n'
    f'{markdown.hbold("Есть варианты:")}\n\n'
    f'{chats_bt.one}:\n Бот вам присылает приглашение в чат, вы вступаете в него и собеседники и вы общаетесь от 3х человек и больше\n\n'
    f'{chats_bt.two}:\n Бот вам присылает {markdown.hcode("имя")} собеседника если вы согласны и ваш собеседник то вы и ваш партнер получаете {markdown.hcode('@username')} друг друга\n' 
)

def error_logger(in_bot: bool, name_func: str = '', e: Exception = None) -> str:
    error_log = None
    
    if in_bot:
        error_log = 'НЕ ПРЕДВИДЕННАЯ ОШИБКА в системе ❗️\n Прошу обратиться к @KociHH'
    
    if e:
        error_log = f'в функции {name_func}:\n {e}'
    
    return error_log

INVISIBLE_PATTERN = re.compile(f"[{''.join(INVISIBLE_CHARS)}]")

def contains_invisible_chars(text: str) -> bool:
    return bool(INVISIBLE_PATTERN.search(text))

def get_invisible_chars(text: str) -> list[str]:
    return [ch for ch in text if ch in INVISIBLE_CHARS]

def remove_invisible(text: str) -> str:
    return ''.join(ch for ch in text if ch not in INVISIBLE_CHARS)

def kats_emodjes() -> str:
    result_kats = ''
    size_kat = random.randint(1, 5)
    len_kats = len(kats)
    for _ in range(size_kat):
        result_kats += kats[random.randint(1, len_kats - 1)]
    
    return result_kats

class ErrorPrefixFilter(logging.Filter):
    def filter(self, record):
        if record.levelno >= logging.ERROR and not record.msg.startswith('[Ошибка]'):
            record.msg = f"[Ошибка] {record.getMessage()}"
        return True
    
async def _send_message_to_user(bot_thread: Bot, target_user_id: int, message_text: str, reply_markup=None) -> Message | None:
    try:
        message_obj = await bot_thread.send_message(
            chat_id=target_user_id,
            text=message_text,
            reply_markup=reply_markup
            )
        return message_obj
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю {target_user_id}: {e}")
        return None
    
