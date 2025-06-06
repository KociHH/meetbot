from operator import le
from winreg import REG_NO_LAZY_FLUSH
from kos_Htools.sql.sql_alchemy.dao import BaseDAO
from .celery_app import celery_app
from data.redis_instance import redis_users, redis_room, redis_random, redis_random_waiting, __redis_users__, __redis_room__, __redis_random__, __redis_random_waiting__
from data.sqlchem import User
from aiogram.utils import markdown
from keyboards.inline_buttons import go_tolk, continue_search_button
from data.utils import CreatingJson
from utils.celery_tools import random_search, count_meetings, RandomMeet, create_private_group
import asyncio
import random
import logging
import time
from utils.time import dateMSC, time_for_redis
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import Message, ReplyKeyboardRemove
from data.middleware.db_middle import session_engine
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import BOT_TOKEN

message_text = 'Идет поиск'
logger = logging.getLogger(__name__)

@celery_app.task
def add_user_to_search(message_id: int, user_id: int, base: str) -> bool:
    """Добавление пользователя в поиск"""
    if base == redis_random:
        data: dict = __redis_random__.get_cached()
        user_id_str = str(user_id)
        rm = RandomMeet(user_id)
        if user_id_str in data.keys():
            if rm.getitem_to_random_user('message_id') != message_id:
                result = rm.getitem_to_random_user(
                    update_many={
                        'message_id': message_id,
                        'data_activity': time_for_redis,
                        },
                    data=data
                    )
            else:
                result = rm.getitem_to_random_user(
                    update_many={
                        'data_activity': time_for_redis,
                        },
                    data=data
                    )
            if result:
                logger.info(f'Обновлен юзер {user_id} в random_users через random_data_user')
                return True
            else:
                logger.error(f'не обновился юзер {user_id}')
                return False
        
        CreatingJson().random_data_user([user_id], {'message_id': message_id})
        logger.info(f'Добавлен новый юзер {user_id} в random_users через random_data_user')
        return True

    elif base == 'party':
        data = __redis_users__.get_cached(redis_users)
        if user_id in data:
            return False
        data.append(user_id)
        __redis_users__.cached(data=data, ex=None)
        return True
    
# patners
@celery_app.task
def remove_user_from_search(user_id: int) -> bool:
    """Удаление пользователя из поиска"""
    rm = RandomMeet(user_id)
    rm.delete_random_user()

@celery_app.task
def monitor_search_users_party():
    """Мониторинг случайного поиска для двух человек"""
    async def _run_task(db_session: AsyncSession):
        data: dict = __redis_random__.get_cached()
        users_data = [key for key in data.keys() if key.isdigit()]
        pair = random_search(users_data, data)

        if pair:
            user1_id, user2_id = pair
            logger.info(f'Найдена потенциальная пара: {user1_id} и {user2_id}')

            # логика после найденной пары
            async def _handle_found_pair(db_session: AsyncSession, user1_id: int, user2_id: int):
                users_meet = [user1_id, user2_id]
                userb = BaseDAO(User, db_session)
                bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                async with bot.session:
                    try:
                        user1_info = await userb.get_one(User.user_id == user1_id)
                        user2_info = await userb.get_one(User.user_id == user2_id)

                        if user1_info and user2_info:
                            try:
                                message_obj1 = await bot.send_message(
                                    chat_id=user1_id,
                                    text=f'Для вас найден собеседник {markdown.hcode(user2_info.pseudonym if user2_info.pseudonym else user2_info.full_name)}.',
                                    reply_markup=go_tolk(msg_id=message_obj1.message_id)
                                )
                                logger.info(f"Отправлено сообщение пользователю {user1_id} о найденной паре {user2_id}.")
                            except Exception as e:
                                logger.error(f"Не удалось отправить сообщение пользователю {user1_id} о найденной паре: {e}.\n {user1_id} будет удален.")
                                remove_user_from_search.delay(user1_id)
                                try:
                                    await bot.send_message(
                                        chat_id=user2_id,
                                        text=f'К сожалению, не удалось связаться с вашим собеседником. Пожалуйста, попробуйте поиск снова.'
                                    )
                                except Exception as e:
                                    logger.error(f"Не удалось оповестить пользователя {user2_id} о неудачной паре: {e}")
                                return None
                            
                            try:
                                message_obj2 = await bot.send_message(
                                    chat_id=user2_id,
                                    text=f'Для вас найден собеседник {markdown.hcode(user1_info.pseudonym if user1_info.pseudonym else user1_info.full_name)}.',
                                    reply_markup=go_tolk(msg_id=message_obj2.message_id)
                                )
                                logger.info(f"Отправлено сообщение пользователю {user2_id} о найденной паре {user1_id}.")
                            except Exception as e:
                                logger.error(f"Не удалось отправить сообщение пользователю {user2_id} о найденной паре: {e}.\n {user2_id} будет удален.")
                                remove_user_from_search.delay(user2_id)
                                try:
                                    await bot.send_message(
                                        chat_id=user1_id,
                                        text=f'К сожалению, не удалось связаться с вашим собеседником. Пожалуйста, попробуйте поиск снова.'
                                    )
                                except Exception as e:
                                    logger.error(f"Не удалось оповестить пользователя {user1_id} о неудачной паре: {e}")
                                return None

                            CreatingJson().random_waiting(users_meet, RandomMeet.meeting_account(data))
                            for user_id_to_process in users_meet:
                                rm = RandomMeet(user_id_to_process)
                                message_id = rm.getitem_to_random_user('message_id')
                                if message_id:
                                    try:
                                        await bot.delete_message(
                                            chat_id=user_id_to_process,
                                            message_id=message_id
                                        )
                                        message_id = None
                                        rm.getitem_to_random_user(item='message_id', change_to=None, _change_provided=True)
                                        logger.info(f"Успешно удалено сообщение анимации для пользователя {user_id_to_process}")
                                    except Exception as e:
                                        logger.error(f"Не удалось удалить сообщение анимации для пользователя {user_id_to_process}: {e}")
                                else:
                                    logger.warning(f'Не найдено message_id юзера {user_id_to_process}, пропускаем')

                        else:
                            logger.error(f'Не удалось получить информацию о пользователях {user1_id} или {user2_id} из БД.')
                    except Exception as e:
                        logger.error(f'Произошла общая ошибка при обработке найденной пары ({user1_id}, {user2_id}): {e}')

            await _handle_found_pair(db_session, user1_id, user2_id)

        # таймер неактивности
        current_time = time.time() 
        for user_id_str, user_info in list(data.items()):
            if not user_id_str.isdigit():
                logger.warning(f'Пропущен нечисловой ключ в данных Redis: {user_id_str}')
                continue

            user_id = int(user_id_str)
            if not isinstance(user_info, dict):
                logger.error(f'Не правильный тип user_info - {type(user_info)} для пользователя {user_id_str}')
                remove_user_from_search.delay(user_id_str).get()
                continue

            added_time = float(user_info.get('added_time', current_time))
            continue_id = user_info.get('continue_id')

            if not isinstance(added_time, (int, float)):
                logger.warning(f'Не числовое значение added_time для пользователя {user_id}: {added_time}. Использование current_time.')
                added_time = current_time

            if current_time - added_time >= 300 and continue_id is None:
                async def _send_timeout_message(user_id: int):
                    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                    async with bot.session:
                        try:
                            message_obj = await bot.send_message(
                                chat_id=user_id,
                                text='Вы тут?\n Нажмите на кнопку либо на любую из доступных.\n Если не ответите через 10 секунд, поиск будет остановлен.',
                                reply_markup=continue_search_button()
                            )
                            return message_obj
                        except Exception as e:
                            logger.error(f'[Ошибка] Не удалось отправить сообщение о продолжении поиска пользователю {user_id}: {e}')
                            return None

                message_obj = await _send_timeout_message(user_id)

                if message_obj:
                    rm = RandomMeet(user_id_str)
                    rm.getitem_to_random_user(
                        update_many={
                            'continue_id': message_obj.message_id,
                            'data_activity': time_for_redis
                            },
                        data=data
                        )
                    check_search_timeout.apply_async(args=[user_id, message_obj.message_id], countdown=10)
                    logger.info(f'Отправлено сообщение о продолжении поиска пользователю {user_id}')

    async def _outer_task():
        async with session_engine() as db_session:
            await _run_task(db_session)

    asyncio.run(_outer_task())

@celery_app.task
def check_search_timeout(user_id: int, message_id: int):
    """Проверка таймаута поиска"""
    data = __redis_random__.get_cached()
    user_id_str = str(user_id)
    if user_id_str in data and isinstance(data[user_id_str], dict) and data[user_id_str].get('continue_id') == message_id:
        logger.info(f'Поиск остановлен для пользователя {user_id} по таймауту (не нажал кнопку).')
        
        async def _stop_animation_timeout(user_id: int, message_id: int):
            bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            async with bot.session:
                try:
                    await bot.edit_message_text(
                        chat_id=user_id,
                        message_id=message_id,
                        text='Поиск остановлен по таймауту.'
                    )
                except Exception as e:
                    logger.error(f'Не удалось остановить анимацию поиска для пользователя {user_id} по таймауту: {e}')

        asyncio.run(_stop_animation_timeout(user_id, message_id))
        remove_user_from_search.delay(user_id_str)
        logger.info(f'Удален из за не активности {user_id_str}')

# party
@celery_app.task
async def create_private_chat(users_party: list) -> dict | None:
    """Создание приватного чата"""
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    async with bot.session:
        chat = await create_private_group(users_party)
        if not chat:
            logger.error('Не удалось создать чат через create_private_group')
            return None
        
        try:
            invite_link = await bot.create_chat_invite_link(
                chat_id=chat.id,
                name="Приватный чат",
                member_limit=2
            )
        except Exception as e:
            logger.error(f'Не удалось создать ссылку приглашения для чата {chat.id}: {e}')
            return None
        
        if not invite_link:
            logger.error(f'не создалась ссылка приглашения для чата: {chat.id}')
            return None
        
        room_data = CreatingJson.rooms(invite_link.invite_link, chat.id, users_party)
        return room_data

@celery_app.task
def animate_search():
    """Периодическая задача для анимации поиска"""
    data = __redis_random__.get_cached()
    animation_frames = ['.', '. .', '. . .']

    async def _run_async_logic(data):
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        async with bot.session:
            async def _edit_message(chat_id: int, message_id: int, text: str):
                try:
                    logger.info(f'Попытка обновить сообщение {message_id} для пользователя {chat_id} с текстом "{text}"')
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"{text}"
                    )
                except Exception as e:
                    logger.error(f'[Ошибка] Не удалось обновить сообщение анимации для пользователя {chat_id} (message_id: {message_id}): {e}')
                    rm = RandomMeet(chat_id)
                    rm.delete_random_user()

            current_second = int(time.time())
            frame_index = current_second % len(animation_frames)
            next_frame_text = animation_frames[frame_index]

            tasks = []
            users_to_update_redis = []
            for user_id_str, user_info in list(data.items()):
                if not user_id_str.isdigit():
                    logger.warning(f'Пропущен нечисловой ключ в данных Redis: {user_id_str}')
                    continue

                user_id = int(user_id_str)
                if isinstance(user_info, dict):
                    message_id = user_info.get('message_id')

                    if message_id is not None:
                        last_animation_text = user_info.get('last_animation_text', '.')
                        calculated_animation_text = f"{next_frame_text}"
                        final_animation_text = calculated_animation_text

                        if calculated_animation_text == last_animation_text:
                            logger.info(f"Текст анимации для пользователя {user_id} (message_id: {message_id}) не изменился. Ищем следующий отличающийся фрейм.")
                            
                            start_index = (frame_index + 1) % len(animation_frames)
                            
                            for i in range(len(animation_frames)):
                                current_index = (start_index + i) % len(animation_frames)
                                frame_candidate_text = f"{animation_frames[current_index]}"
                                
                                if frame_candidate_text != last_animation_text:
                                    final_animation_text = frame_candidate_text
                                    logger.info(f"Найден отличающийся фрейм: {final_animation_text}")
                                    break

                        if final_animation_text != last_animation_text:
                             print(f"Обновление анимации для пользователя {user_id} (message_id: {message_id}) на текст: {final_animation_text}")
                             tasks.append(_edit_message(user_id, message_id, final_animation_text))
                             users_to_update_redis.append((user_id_str, final_animation_text))
                        else:
                             logger.warning(f"Не удалось найти отличающийся фрейм для пользователя {user_id}. Пропускаем обновление.")
                    else:
                        logger.warning(f'Не удалось получить message_id для пользователя {user_id}. Сообщение об ошибке не отправлено.')
                else:
                    logger.error(f'Не правильный тип user_info - {type(user_info)} для пользователя {user_id_str}')
                    rm = RandomMeet(user_id)
                    rm.delete_random_user()

            if tasks:
                await asyncio.gather(*tasks)
                for user_id_str, new_text in users_to_update_redis:
                     if user_id_str in data and isinstance(data[user_id_str], dict):
                        data[user_id_str]['last_animation_text'] = new_text
                     else:
                        logger.warning(f'Не удалось обновить last_animation_text для пользователя {user_id_str}, так как он не найден или имеет некорректный формат в Redis.')
                __redis_random__.cached(data=data, ex=None)

    asyncio.run(_run_async_logic(data))

@celery_app.task
def update_statistics():
    """Обновление статистики"""
    stats = {
        "searching_users_party": len(__redis_users__.get_cached()),
        "total_chats": len(__redis_room__.get_cached()),

        "searching_patners": len(__redis_random__.get_cached()),
        "waiting_random": len(__redis_random_waiting__.get_cached())
    }
    print(stats)
    return stats