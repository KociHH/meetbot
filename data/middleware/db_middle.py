import asyncio
import logging
from aiogram import BaseMiddleware
from fastapi.middleware import Middleware
from sqlalchemy import create_engine, select, pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import TelegramObject, CallbackQuery, Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from config import BD_URL_POSTGRES
from ..redis_instance import __redis_room__, __redis_users__
from keyboards.callback_datas import Subscriber

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
                logger.error(f'Ошибка в middleware: {e}, class: {__class__.__name__}')

class listclonWare(BaseMiddleware):
    def __init__(self, users_list: list, target_handler: str, max_iterations: int = 100) -> None:
        super().__init__()
        self.users_list = users_list
        self.target_handler = target_handler
        self.max_iterations = max_iterations
        self.iteration_count = 0
        self.is_activated = False

    async def __call__(
            self, 
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
            ) -> Any:
        current_handler = handler.__name__ if hasattr(handler, '__name__') else str(handler)
        logger.info(f'Текущий хендлер: {current_handler}, Целевой хендлер: {self.target_handler}')

        if current_handler != self.target_handler or not isinstance(event, Message) or event.text != '/find':
            return await handler(event, data)
            
        self.iteration_count += 1
        logger.info(f'Команда /find: Итерация {self.iteration_count} из {self.max_iterations}')
        
        if self.iteration_count >= self.max_iterations and not self.is_activated:
            self.is_activated = True
            logger.info(f'Достигнут лимит {self.max_iterations} использований команды /find. Запуск обработки...')
            
            try:
                result_data = []
                if self.users_list and isinstance(self.users_list, list):
                    unique_users = set(self.users_list)
                    result_data = list(unique_users)
                    logger.info(f'Найдено {len(self.users_list) - len(result_data)} дубликатов')
                else:
                    logger.info(f'{self.users_list} пустой')
                
                data['result_data'] = result_data
                gett = __redis_users__.get_cashed()
                gett = result_data

                __redis_users__.cashed(key='useactive_users', data=gett, ex=0)
                logger.info(f'Обработка пользователей завершена, данные сохранены {result_data}')
                
                self.iteration_count = 0
                self.is_activated = False
                
            except Exception as e:
                logger.error(f'Ошибка при обработке пользователей: {e}, class: {__class__.__name__}')
        
        return await handler(event, data)
    
class checkerChannelWare(BaseMiddleware):
    def __init__(self, channel: int | str) -> None:
        self.channel = channel.replace('@', '') if isinstance(channel, str) else channel
        super().__init__()

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject, 
            data: Dict[str, Any]
            ) -> Any:
        try:
            user_id = event.from_user.id

            if isinstance(self.channel, str):
                channel_info = await event.bot.get_chat(self.channel)
                channel_id = channel_info.id
            else:
                channel_id = self.channel

            user_status = await event.bot.get_chat_member(channel_id, user_id)
            
            if user_status.status not in ['member', 'administrator', 'creator']:
                data['is_subscribed'] = False
                return await handler(event, data)
            else:
                data['is_subscribed'] = True
                
                text = event.text
                if isinstance(event, Message) and text and text.startswith('/'):
                    data['saved_command'] = event.text
                
                sub_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="📢 Подписаться на канал",
                                url=f'https://t.me/{self.channel}'
                            ),
                            InlineKeyboardButton(
                                text='Проверка подписки на канал 🙏',
                                callback_data=Subscriber.check_button
                            )
                        ]
                    ]
                )

                if isinstance(event, Message):
                    await event.answer(
                        "Для использования бота необходимо подписаться на наш канал:",
                        reply_markup=sub_keyboard
                    )
                return None
        
        except Exception as e:
            logger.error(f'Ошибка при проверке подписки: {e}, class: {__class__.__name__}')
            return await handler(event, data)


class CheckActivityChat(BaseMiddleware):
    def __init__(self, ) -> None:
        super().__init__()

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]) -> Any:


        result = handler(event, data)
        return await result
            
    
    
    