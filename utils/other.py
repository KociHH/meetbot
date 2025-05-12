from commands.message_bot import menu_chats
import logging
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def error_logger(in_bot: bool, name_func: str, e = None) -> str:
    error_bot = None
    error_log = None
    
    if in_bot:
        error_bot = 'Ошибка в системе ❗️\n Прошу обратиться к @KociHH'
    
    if e:
        error_log = f'Ошибка в функции {name_func}:\n {e}'
    
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
