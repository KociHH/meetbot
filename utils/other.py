import random
import re
from commands.message_bot import menu_chats
import logging
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils import markdown
from keyboards.button_names import chats_bt
from keyboards.reply_button import chats
from commands.state import Menu_chats
from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from aiogram.enums import ParseMode
from .words_or_other import INVISIBLE_CHARS, kats
from data.redis_instance import redis_random, random_users, redis_random_waiting

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

hello_text = markdown.text(
    f'Привет'
    f'Этот бот предназначен для быстрых знакомств\n'
    f'{markdown.hblockquote("Есть варианты:")}\n\n'
    f'[1] Бот вам присылает приглашение в чат, вы вступаете в него и собеседник и вы общаетесь от 3x человек\n\n'
    f'[2] Бот вам присылает {markdown.hpre("@username")} собеседника если вы согласны и ваш собеседник то вы и ваш партнер получаете {markdown.hpre('@username')} друг друга\n' 
)

async def menu_chats(message: Message, state: FSMContext, edit: bool = False):
    message_obj = message.answer
    if edit:
        message_obj = message.edit_text

    await message_obj(
        text=f"{hello_text}",
            reply_markup=chats()
            )
    await state.set_state(Menu_chats.system_chats)


def error_logger(in_bot: bool, name_func: str = '', e: Exception = None) -> str:
    error_bot = None
    error_log = None
    
    if in_bot:
        error_bot = '[Ошибка] в системе ❗️\n Прошу обратиться к @KociHH'
    
    if e:
        error_log = f'[Ошибка] в функции {name_func}:\n {e}'
    
    return error_bot, error_log


async def import_functions(x: str, message: Message, state: FSMContext = None, db_session: AsyncSession = None):
    try:
        if x == 'menu_chats':
            await menu_chats(message, state, db_session)
        else:
            logger.error('Такой функции нет')
            return
    except Exception as e:
        logger.error(f'Ошибка в import_functions: {e}')


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


def count_meetings() -> int:
    data = redis_random_waiting.redis_data()
    if not data:
        return 1
    
    meetings = sorted(int(meet) for meet in data.keys())
    dynamic_count = 1

    for meet in meetings:
        if meet == dynamic_count:
            dynamic_count += 1
        else:
            break
    return dynamic_count


def changes_to_random_waiting(user_id: int, field: str | int, value):
    data = redis_random_waiting.redis_data()

    for room_id, room_info in data.items():
        users: dict = room_info.get('users', {})

        if user_id in users:
            users[user_id][field] = value
            redis_random_waiting.redis_cashed(data=data)

            return room_id, True, users
    return None, False, None

def delete_meet(count_meet: int):
    data = redis_random_waiting.redis_data()
    data.pop(count_meet) if isinstance(data, dict) else logger.error(f'Не тот тип {type(data)}')
    redis_random_waiting.redis_cashed(data=data, ex=None)
    return data
