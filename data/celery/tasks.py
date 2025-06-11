from datetime import datetime, timedelta
from operator import le
from unittest import result
import venv
from winreg import REG_NO_LAZY_FLUSH
from kos_Htools.sql.sql_alchemy.dao import BaseDAO
from data.mongo.config import party_searchers, many_searchers
from keyboards.callback_datas import ContinueSearch
from .celery_app import celery_app
from data.redis_instance import redis_users, redis_room, redis_random, redis_random_waiting, __redis_users__, __redis_room__, __redis_random__, __redis_random_waiting__
from data.sqlchem import User
from aiogram.utils import markdown
from keyboards.inline_buttons import go_tolk, continue_search_button
from data.utils import CreatingJson
from utils.other import _send_message_to_user
from utils.celery_tools import details_fromDB, random_search, count_meetings, RandomMeet, create_private_group
import asyncio
import random
import logging
import time
from utils.time import DateMoscow, dateMSC, moscow_time, time_for_redis
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import Message, ReplyKeyboardRemove
from data.middleware.db_middle import session_engine
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import BOT_TOKEN
import pytz


message_text = 'Идет поиск'
logger = logging.getLogger(__name__)

@celery_app.task
def add_user_to_search(message_id: int, user_id: int, base: str) -> bool:
    """Добавление пользователя в поиск"""
    print("\n\n=============================================== SEARCH INFO ===============================================\n\n")

    if base == redis_random:
        data: dict = __redis_random__.get_cached()
        user_id_str = str(user_id)
        rm = RandomMeet(user_id_str)
        if user_id_str in data.keys():
            if rm.getitem_to_random_user('message_id', data=data) != message_id:
                result = rm.getitem_to_random_user(
                    update_many={
                        'message_id': message_id,
                        'data_activity': time_for_redis,
                        'online_searching': True
                        },
                    data=data
                    )
            else:
                result = rm.getitem_to_random_user(
                    update_many={
                        'data_activity': time_for_redis,
                        'online_searching': True
                        },
                    data=data
                    )
            if result:
                logger.info(f'Обновлен юзер {user_id} в random_users через getitem_to_random_user')
                return None
            else:
                logger.error(f'не обновился юзер {user_id}')
                return None
        
        CreatingJson().random_data_user(
            users=[user_id],
            value={
                'message_id': message_id,
                'online_searching': True
              },
            main_data=data
            )
        logger.info(f'Добавлен новый юзер {user_id} в random_users В поиск через random_data_user')
        print("\n\n===========================================================================================================\n\n")
        return None

    elif base == 'party':
        data = __redis_users__.get_cached(redis_users)
        if user_id in data:
            return None
        data.append(user_id)
        __redis_users__.cached(data=data, ex=None)
        print("\n\n===========================================================================================================\n\n")
        return None

# patners
@celery_app.task
def remove_user_from_search(user_id: int) -> bool:
    """Полное удаление пользователя из поиска"""
    rm = RandomMeet(user_id)
    rm.delete_random_user()

@celery_app.task
def monitor_search_users_party():
    """Мониторинг случайного поиска для двух человек"""
    async def _run_task(db_session: AsyncSession):
        print("\n\n=============================================== PARTNERS INFO ===============================================\n\n")
        data: dict = __redis_random__.get_cached()

        users_data = [us for us in data.keys() if us.isdigit() and RandomMeet(us).getitem_to_random_user(item='online_searching', data=data)]
        pair = random_search(users_data, data)

        if pair:
            user1_id, user2_id = pair
            logger.info(f'Найдена потенциальная пара: {user1_id} и {user2_id}')

            async def _handle_found_pair(db_session: AsyncSession, user1_id: int, user2_id: int):
                users_meet = [user1_id, user2_id]
                bot_thread = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

                async with bot_thread.session:
                    try:
                        full_data_users = await details_fromDB(
                            db_session=db_session,
                            users=users_meet,
                            name_or_pseudonym=True,
                        )

                        if not full_data_users or len(full_data_users) < 2:
                            logger.error(f'Не удалось получить информацию о пользователях {user1_id} или {user2_id} из БД или не все пользователи найдены.')
                            return None

                        user_names = {}
                        for uid in users_meet:
                            user_info: dict = full_data_users.get(uid)
                            user_names[uid] = user_info.get('name_or_pseudonym') or user_info.get('user_inf').full_name

                        user1_msg_obj = await _send_message_to_user(
                            bot_thread=bot_thread,
                            target_user_id=user1_id,
                            message_text=f'🔔 Для вас найден собеседник -> {markdown.hcode(user_names[user2_id])}',
                            reply_markup=go_tolk()
                        )

                        user2_msg_obj = await _send_message_to_user(
                            bot_thread=bot_thread,
                            target_user_id=user2_id,
                            message_text=f'🔔 Для вас найден собеседник -> {markdown.hcode(user_names[user1_id])}',
                            reply_markup=go_tolk()
                        )

                        if not user1_msg_obj and not user2_msg_obj:
                            logger.error(f"Не удалось отправить сообщения обоим пользователям. {user1_id}: {user1_msg_obj}, {user2_id}: {user2_msg_obj}.\n Будут удалены")
                            for uid in users_meet:
                                remove_user_from_search.delay(uid)
                                await _send_message_to_user(
                                    bot_thread=bot_thread,
                                    target_user_id=uid,
                                    message_text='К сожалению, не удалось связаться с вашим собеседником. Пожалуйста, попробуйте поиск снова.',
                                    reply_markup=continue_search_button()
                                )
                            return None
                        
                        elif not user1_msg_obj:
                            logger.error(f"Пользователь {user1_id} будет удален из поиска (не удалось отправить начальное сообщение).")
                            remove_user_from_search.delay(user1_id)
                            if user2_msg_obj:
                                await _send_message_to_user(
                                    bot_thread=bot_thread,
                                    target_user_id=user2_id,
                                    message_text='К сожалению, не удалось связаться с вашим собеседником. Пожалуйста, попробуйте поиск снова.',
                                    reply_markup=continue_search_button(ContinueSearch.continue_search)
                                )
                            return None
                        
                        elif not user2_msg_obj:
                            logger.error(f"Пользователь {user2_id} будет удален из поиска (не удалось отправить начальное сообщение).")
                            remove_user_from_search.delay(user2_id)
                            if user1_msg_obj:
                                await _send_message_to_user(
                                    bot_thread=bot_thread,
                                    target_user_id=user1_id,
                                    message_text='К сожалению, не удалось связаться с вашим собеседником. Пожалуйста, попробуйте поиск снова.',
                                    reply_markup=continue_search_button(ContinueSearch.continue_search)
                                )
                            return None

                        meet_created = CreatingJson().random_waiting(users=users_meet, num_meet=RandomMeet.meeting_account())
                        if not meet_created:
                            logger.error(f'Не создалась комната для: {user1_id}/{user2_id}. Оба пользователя будут удалены из поиска.')
                            for uid in users_meet:
                                remove_user_from_search.delay(uid)
                                await _send_message_to_user(bot_thread, uid, 'Произошла ошибка при создании чата. Пожалуйста, попробуйте поиск снова.', reply_markup=continue_search_button(ContinueSearch.continue_search))
                            return None

                        for uid, ms in zip(users_meet, [user1_msg_obj, user2_msg_obj]):
                            rm = RandomMeet(uid)
                            message_count = int(rm.getitem_to_random_user(item='message_count'))
                            new_message_count = message_count + 1 if isinstance(message_count, int) else 2

                            rm.getitem_to_random_waiting(field='message_id', value=ms.message_id, complete_update=True)
                            rm.getitem_to_random_user(item='message_count', change_to=new_message_count, _change_provided=True)
                        logger.info(f'Добавлены message_id и message_count для '
                                    f'{user1_id} ({user1_msg_obj.message_id}, {new_message_count}) и '
                                    f'{user2_id} ({user2_msg_obj.message_id}, {new_message_count})'
                                    )

                        for uid_to_clean in users_meet:
                            rm = RandomMeet(uid_to_clean)
                            deactivating_search = rm.getitem_to_random_user(
                                update_many={
                                    'online_searching': False,
                                    'last_animation_text': None,
                                    'added_time': None,
                                },
                                _change_provided=True,
                            )
                            if not deactivating_search:
                                logger.error(f'Не изменены данные {uid_to_clean} для деактивации поиска.')

                            message_id_to_delete = rm.getitem_to_random_user(item='message_id')
                            if message_id_to_delete:
                                try:
                                    await bot_thread.delete_message(
                                        chat_id=uid_to_clean,
                                        message_id=message_id_to_delete
                                    )
                                    rm.getitem_to_random_user(item='message_id', change_to=None, _change_provided=True)
                                    logger.info(f"Успешно удалено сообщение анимации для пользователя {uid_to_clean}.")
                                except Exception as e:
                                    logger.error(f"Не удалось удалить сообщение анимации для пользователя {uid_to_clean}: {e}")
                            else:
                                logger.warning(f'Не найдено message_id юзера {uid_to_clean}, пропускаем удаление анимации.')

                        return users_meet

                    except Exception as e:
                        logger.error(f'Произошла общая ошибка при обработке найденной пары ({user1_id}, {user2_id}): {e}. Оба пользователя будут удалены из поиска.')
                        for uid in users_meet:
                            remove_user_from_search.delay(uid)
                            await _send_message_to_user(bot_thread, uid, 'Произошла непредвиденная ошибка. Пожалуйста, попробуйте поиск снова.', reply_markup=continue_search_button(ContinueSearch.continue_search))
                        return None

            await _handle_found_pair(db_session, user1_id, user2_id)
            print("\n\n=============================================================================================================\n\n")

    async def _outer_task():
        async with session_engine() as db_session:
            await _run_task(db_session)

    asyncio.run(_outer_task())
    print("\n\n=============================================================================================================\n\n")

@celery_app.task
def check_search_timeout(user_id: int, message_id: int):
    """Проверка таймаута поиска"""
    rm = RandomMeet(user_id)
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
        rm.getitem_to_random_user(item='online_searching', change_to=False, _change_provided=True)
        logger.info(f'Бот остановил поиск для {user_id_str} из за не активности')

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
    print("\n\n=============================================== ANIMATE INFO ===============================================\n\n")
    data = __redis_random__.get_cached()
    animation_frames = ['.', '. .', '. . .']

    async def _run_async_logic(data: dict):
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
            for user_id_str, user_info in data.items():
                rm = RandomMeet(user_id_str)
                if not user_id_str.isdigit():
                    logger.warning(f'Пропущен нечисловой ключ в данных Redis: {user_id_str}')
                    continue

                online_searching = rm.getitem_to_random_user(item='online_searching', data=data)
                if online_searching is False:
                    continue

                user_id = int(user_id_str)
                if isinstance(user_info, dict):
                    message_id = user_info.get('message_id')

                    if message_id is not None:
                        last_animation_text = user_info.get('last_animation_text', '.')
                        calculated_animation_text = f"{next_frame_text}"
                        final_animation_text = calculated_animation_text

                        if calculated_animation_text == last_animation_text:
                            
                            start_index = (frame_index + 1) % len(animation_frames)
                            
                            for i in range(len(animation_frames)):
                                current_index = (start_index + i) % len(animation_frames)
                                frame_candidate_text = f"{animation_frames[current_index]}"
                                
                                if frame_candidate_text != last_animation_text:
                                    final_animation_text = frame_candidate_text
                                    break

                        if final_animation_text != last_animation_text:
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
    print("\n\n============================================================================================================\n\n")

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

@celery_app.task
def check_inactivity_timeout():
    """Проверяет неактивных пользователей и отправляет им уведомления или удаляет из поиска."""
    print("\n\n=============================================== INACTIVE INFO ===============================================\n\n")
    async def _run_inactivity_check():
        data: dict = __redis_random__.get_cached()
        current_time = time.time()
        bot_instance = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

        async with bot_instance.session:
            async def _send_message_to_user_inactivity(bot_thread: Bot, target_user_id: int, message_text: str, reply_markup=None) -> Message | None:
                """Вспомогательная функция для отправки сообщения пользователю и обработки ошибок отправки (для таймера неактивности)."""
                try:
                    message_obj = await bot_thread.send_message(
                        chat_id=target_user_id,
                        text=message_text,
                        reply_markup=reply_markup
                    )
                    logger.info(f"Успешно отправлено сообщение пользователю {target_user_id}.")
                    return message_obj
                except Exception as e:
                    logger.error(f"Не удалось отправить сообщение пользователю {target_user_id}: {e}")
                    return None

            for user_id_str, user_info in data.items():
                rm = RandomMeet(user_id_str)
                online_searching = rm.getitem_to_random_user(item='online_searching', data=data)

                if online_searching is False:
                    logger.info(f'В данный момент {user_id_str} не в поиске (ласт активность: {rm.getitem_to_random_user(item='data_activity')})')
                    continue

                if not user_id_str.isdigit():
                    logger.warning(f'Пропущен нечисловой ключ в данных Redis: {user_id_str}')
                    continue

                user_id = int(user_id_str)
                if not isinstance(user_info, dict):
                    logger.error(f'Не правильный тип user_info - {type(user_info)} для пользователя {user_id_str}')
                    remove_user_from_search.delay(user_id_str)
                    continue

                added_time_value = user_info.get('added_time')
                if added_time_value is None:
                    added_time = current_time
                else:
                    try:
                        added_time = float(added_time_value)
                    except (ValueError, TypeError):
                        logger.warning(f'Некорректное значение added_time для пользователя {user_id}: {added_time_value}. Использование current_time.')
                        added_time = current_time

                continue_id = user_info.get('continue_id')

                print(f'current_time: {current_time}, added_time: {added_time}\n user_id: {user_id}')
                if current_time - added_time >= 600 and continue_id is None:
                    message_obj = await _send_message_to_user_inactivity(
                        bot_thread=bot_instance,
                        target_user_id=user_id,
                        message_text='Вы тут?\n Нажмите на кнопку снизу.\n Если не ответите через 10 секунд, поиск будет остановлен.',
                        reply_markup=continue_search_button(ContinueSearch.continue_search)
                    )

                    if message_obj:
                        rm = RandomMeet(user_id_str)
                        rm.getitem_to_random_user(
                            update_many={
                                'continue_id': message_obj.message_id,
                                'data_activity': time_for_redis
                                },
                            )
                        check_search_timeout.apply_async(args=[user_id, message_obj.message_id], countdown=10)
                        logger.info(f'Отправлено сообщение о продолжении поиска пользователю {user_id}')

    asyncio.run(_run_inactivity_check())
    print("\n\n=============================================================================================================\n\n")

@celery_app.task
def moving_inactive_users_to_mongo() -> None:
    """Добавление в mongo_db и удаление из памяти redis неактивных юзеров"""
    print("\n\n=============================================== TRANSLATION INACTIVE TO MONGODB INFO ===============================================\n\n")
    try:
        end_log = "\n\n====================================================================================================================================\n\n"
        data_random: dict = __redis_random__.get_cached()
        user_sets = []
        uids_to_delete = []

        for uid, value in data_random.items():
            data_data = value['data_activity']

            if data_data is not None and isinstance(data_data, str):
                date_conversion = datetime.fromisoformat(data_data)

                if date_conversion.tzinfo is None:
                    date_conversion = pytz.utc.localize(date_conversion).astimezone(moscow_time)
                else:
                    date_conversion = date_conversion.astimezone(moscow_time)

                if (datetime.now(moscow_time) - date_conversion).total_seconds() / 60 >= 60:
                    user_sets.append(data_random[uid])
                    uids_to_delete.append(uid)

        size = len(user_sets)

        if not user_sets:
            logger.info(f'user_sets был пустой -size: {size}')
            print(end_log)
            return 

        for user_id in uids_to_delete:
            rm = RandomMeet(user_id)
            rm.delete_random_user()
        
        if size >= 2:
            party_searchers.insert_many(user_sets)
            logger.info(f'Были добавленны данные в mongo_db в таблицу party_searchers -size: {size}')
        
        elif size < 2:
            party_searchers.insert_one(user_sets[0])
            logger.info(f'Был добавлен один элемент в mongo_db в таблицу party_searchers -size: {size}')

        print(end_log)
        return
    
    except Exception as e:
        logger.error(f'в таске moving_inactive_users_to_mongo:\n {e}')
        print(end_log)
        return
    

