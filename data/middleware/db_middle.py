import asyncio
import logging
from aiogram import BaseMiddleware
from fastapi.middleware import Middleware
from sqlalchemy import create_engine, select, pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import TelegramObject, CallbackQuery, Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberLeft
from config import BD_URL_POSTGRES, ADMIN_ID
from ..redis_instance import __redis_room__, __redis_users__
from keyboards.inline_buttons import sub_keyboard

logger = logging.getLogger(name=__name__)

engine = create_async_engine(url=BD_URL_POSTGRES, echo=False, future=True, poolclass=pool.NullPool)
session_engine = async_sessionmaker(engine, expire_on_commit=False,  class_=AsyncSession)

class WareBase(BaseMiddleware):
    def __init__(self, async_session: async_sessionmaker):
        super().__init__()
        self.async_session = async_session

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self.async_session() as session:
            data['db_session'] = session
            try:
                post_date = await handler(event, data)
                await session.commit()
                return post_date
            except Exception as e:
                await session.rollback()
                logger.exception(f'Ошибка в middleware: {e}, class: {__class__.__name__}')
                raise
    
class checkerChannelWare(BaseMiddleware):
    def __init__(self, channel: int | str) -> None:
        super().__init__()
        self.channel = channel
        
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject, 
            data: Dict[str, Any]
            ) -> Any:
        try:
            user_id = event.from_user.id

            if user_id in ADMIN_ID:
                return await handler(event, data)
            
            user_status = await event.bot.get_chat_member(self.channel, user_id)

            if isinstance(user_status, ChatMemberLeft):
                if isinstance(event, Message):
                    await event.answer(
                        "‼️ Для использования бота необходимо подписаться на наш канал.",
                        reply_markup=sub_keyboard()
                    )
                return None
            else:
                return await handler(event, data)
        
        except Exception as e:
            logger.error(f'Ошибка при проверке подписки: {e}, class: {__class__.__name__}')
            return await handler(event, data)
            
    