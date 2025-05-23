from kos_Htools import BaseDAO
from .celery_app import celery_app
from data.redis_instance import users, random_users, redis_random, redis_random_waiting, room, redis_users
from data.sql_instance import userb
from data.sqlchem import User
from aiogram.utils import markdown
from keyboards.inline_buttons import go_tolk, continue_search_button
from data.utils import CreatingJson
from utils.other_celery import random_search, count_meetings, RandomMeet, bot
import asyncio
import random
import logging
import time
from utils.time import dateMSC
from sqlalchemy.ext.asyncio import AsyncSession

message_text = 'Идет поиск'
logger = logging.getLogger(__name__)

@celery_app.task
def add_user_to_search(message_id: int, user_id: int, base: str) -> bool:
    """Добавление пользователя в поиск"""
    if base == redis_random:
        data = random_users.redis_data()
        user_id_str = str(user_id)
        
        if user_id_str in data:
            if data[user_id_str].get('message_id') != message_id:
                 CreatingJson().random_data_user([user_id], {'message_id': message_id, 'last_activity': dateMSC})
            else:
                 CreatingJson().random_data_user([user_id], {'last_activity': dateMSC})
            print(f'Обновлен юзер {user_id} в random_users через random_data_user')
            return False
        
        CreatingJson().random_data_user([user_id], {'message_id': message_id})
        print(f'Добавлен новый юзер {user_id} в random_users через random_data_user')
        return True

    elif base == 'party':
        data = users.redis_data()
        if user_id in data:
            return False
        data.append(user_id)
        users.redis_cashed(data=data, ex=None)
        return True
    
# patners
@celery_app.task
def remove_user_from_search(user_id: int) -> bool:
    """Удаление пользователя из поиска"""
    rm = RandomMeet(user_id)
    rm.delete_random_user(user_id)

@celery_app.task
def monitor_search_users_party(db_session: AsyncSession):
    """Мониторинг случайного поиска для двух человек"""
    data = random_users.redis_data()
    user_ids_list = list(data.keys())
    len_data = len(user_ids_list)

    if not data:
        return None

    if len_data >= 2:
        pair = random_search(redis_random, len_data)

        if pair:
            user1_id, user2_id = pair
            logger.info(f'Найдена потенциальная пара: {user1_id} и {user2_id}')

            async def search_users_party(user1_id: int, user2_id: int):
                try:
                    user1_info = await userb.get_one(db_session, User.user_id == user1_id)
                    user2_info = await userb.get_one(db_session, User.user_id == user2_id)

                    if user1_info and user2_info:
                        await bot.send_message(chat_id=user1_id, text=f'Для вас найден собеседник {markdown.hpre(user2_info.pseudonym if user2_info.pseudonym else user2_info.full_name)}.')
                        await bot.send_message(chat_id=user2_id, text=f'Для вас найден собеседник {markdown.hpre(user1_info.pseudonym if user1_info.pseudonym else user1_info.full_name)}.')
                        try:
                            if data.get(str(user1_id), {}).get('message_id'):
                                await bot.delete_message(chat_id=user1_id, message_id=data[str(user1_id)]['message_id'])
                            if data.get(str(user2_id), {}).get('message_id'):
                                await bot.delete_message(chat_id=user2_id, message_id=data[str(user2_id)]['message_id'])
                        except Exception as e:
                            logger.error(f'[Ошибка] Не удалось удалить сообщения анимации поиска для пользователей {user1_id} и {user2_id}: {e}')
                    else:
                        logger.error(f'[Ошибка] Не удалось получить информацию о пользователях {user1_id} или {user2_id}')
                except Exception as e:
                    logger.error(f'[Ошибка] Не удалось отправить сообщения пользователям {user1_id} и {user2_id}: {e}')

            asyncio.run(search_users_party(user1_id, user2_id))

    current_time = time.time()
    for user_id_str, user_info in list(data.items()):
        user_id = int(user_id_str)
        added_time = user_info.get('added_time', current_time)
        message_id = user_info.get('continue_id')

        if current_time - added_time > 300 and message_id is None:
            try:
                async def _send_timeout_message(user_id: int):
                    message_obj = await bot.send_message(
                        chat_id=user_id,
                        text='Продолжить поиск?\n Если не ответите через 10 секунд, поиск будет остановлен.',
                        reply_markup=continue_search_button()
                    )
                    return message_obj

                message_obj = asyncio.run(_send_timeout_message(user_id))

                data[user_id_str]['continue_id'] = message_obj.message_id
                data[user_id_str]['data_activity'] = dateMSC
                random_users.redis_cashed(data=data, ex=None)

                check_search_timeout.apply_async(args=[user_id, message_obj.message_id], countdown=10)
                logger.info(f'Отправлено сообщение о продолжении поиска пользователю {user_id}')
            except Exception as e:
                 logger.error(f'[Ошибка] Не удалось отправить сообщение о продолжении поиска пользователю {user_id}: {e}')

@celery_app.task
def check_search_timeout(user_id: int, message_id: int):
    """Проверка таймаута поиска"""
    data = random_users.redis_data()
    user_id_str = str(user_id)
    rm = RandomMeet(user_id)
    if user_id_str in data and data[user_id_str].get('continue_id') == message_id:
        logger.info(f'Поиск остановлен для пользователя {user_id} по таймауту (не нажал кнопку).')
        
        async def _stop_animation_timeout(user_id: int, message_id: int):
            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=message_id,
                    text='Поиск остановлен по таймауту.'
                )
            except Exception as e:
                logger.error(f'[Ошибка] Не удалось остановить анимацию поиска для пользователя {user_id} по таймауту: {e}')

        asyncio.run(_stop_animation_timeout(user_id, message_id))
        rm.delete_random_user(user_id)

# party
@celery_app.task
async def create_private_chat(users_party: list, db_session: AsyncSession) -> dict | None:
    """Создание приватного чата"""
    from utils.db_work import create_private_group
    chat = await create_private_group(db_session)
    if not chat:
        logger.error('[Ошибка] Не удалось создать чат через create_private_group')
        return None
        
    try:
        invite_link = await bot.create_chat_invite_link(
            chat_id=chat.id,
            name="Приватный чат",
            member_limit=2
        )
    except Exception as e:
        logger.error(f'[Ошибка] Не удалось создать ссылку приглашения для чата {chat.id}: {e}')
        return None
    
    if not invite_link:
        logger.error(f'[Ошибка] не создалась ссылка приглашения для чата: {chat.id}')
        return None
        
    room_data = CreatingJson.rooms(invite_link.invite_link, chat.id, users_party)
    return room_data


@celery_app.task
def animate_search():
    """Периодическая задача для анимации поиска"""
    data = random_users.redis_data()
    animation_frames = ['.', '..', '...']

    async def _edit_message(chat_id: int, message_id: int, text: str):
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{message_text} {text}"
            )
        except Exception as e:
            logger.error(f'[Ошибка] Не удалось обновить сообщение анимации для пользователя {chat_id} (message_id: {message_id}): {e}')
            rm = RandomMeet(chat_id)
            rm.delete_random_user()

    current_second = int(time.time())
    frame_index = current_second % len(animation_frames)
    next_frame_text = animation_frames[frame_index]

    for user_id_str, user_info in list(data.items()):
        user_id = int(user_id_str)
        message_id = user_info.get('message_id')

        if message_id is not None:
            asyncio.run(_edit_message(user_id, message_id, next_frame_text))

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(5.0, monitor_search_users_party.s(), name='random search')
    sender.add_periodic_task(5.0, animate_search.s(), name='search animation')
    print(f'Прошла попытка таски sender: \n{sender}')

@celery_app.task
def update_statistics():
    """Обновление статистики"""
    stats = {
        "searching_users_party": len(users.redis_data()),
        "total_chats": len(room.redis_data()),
        "searching_patners": len(random_users.redis_data())
    }
    return stats