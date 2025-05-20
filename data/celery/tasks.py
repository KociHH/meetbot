from celery_app import celery_app
from data.redis_instance import users, random_users, redis_random, redis_random_waiting, room, redis_users
from utils.db_work import create_private_group
from data.sql_instance import userb
from data.sqlchem import User
from utils.other import RandomMeet, bot
from aiogram.utils import markdown
from keyboards.inline_buttons import go_tolk, continue_search_button
from data.utils import CreatingJson
from utils.other import count_meetings, delete_random_user, delete_meet
import asyncio
import random
import logging
import time
from utils.time import dateMSC


logger = logging.getLogger(__name__)

@celery_app.task
def add_user_to_search(user_id: int, base: str) -> bool:
    """Добавление пользователя в поиск"""
    if base == 'random_meet':
        data = random_users.redis_data()
        if str(user_id) in data:
            data[str(user_id)]['data_activity'] = dateMSC
            random_users.redis_cashed(data=data, ex=None)
            return False
        data[str(user_id)] = {
            'added_time': time.time(),
            'message_id': None,
            'skip_users': [],
            'tolk_users': [],
            'data_activity': dateMSC
        }
        random_users.redis_cashed(data=data, ex=None)
        return True
    
    elif base == 'party':
        data = users.redis_data()
        if user_id in data:
            return False
        data.append(user_id)
        users.redis_cashed(data=data, ex=None)
        return True

@celery_app.task
def remove_user_from_search(user_id: int) -> bool:
    """Удаление пользователя из поиска"""
    rm = RandomMeet(user_id)
    rm.delete_random_user(user_id)

@celery_app.task
def create_private_chat(users_party: list) -> dict:
    """Создание приватного чата"""
    chat = asyncio.run(create_private_group())
    if not chat:
        return None
        
    invite_link = asyncio.run(bot.create_chat_invite_link(
        chat_id=chat.id,
        name="Приватный чат",
        member_limit=2
    ))
    
    if not invite_link:
        logger.error(f'[Ошибка] не создался чат: {chat.id}')
        return None
        
    room_data = CreatingJson.rooms(invite_link.invite_link, chat.id, users_party)
    return room_data

@celery_app.task
def update_statistics():
    """Обновление статистики"""
    stats = {
        "active_users": len(users.redis_data()),
        "total_chats": len(room.redis_data()),
        "searching_users": len(random_users.redis_data())
    }
    return stats

@celery_app.task
def monitor_random_search():
    """Мониторинг случайного поиска"""
    data = random_users.redis_data()
    user_ids = list(data.keys())
    random.shuffle(user_ids)

    i = 0
    while i < len(user_ids) - 1:
        user1_id = int(user_ids[i])
        user2_id = int(user_ids[i+1])

        if str(user1_id) in random_users.redis_data() and str(user2_id) in random_users.redis_data():

            users_party = [user1_id, user2_id]
            chat_data = asyncio.run(create_private_chat(users_party))

            if chat_data:
                logger.info(f'Создан чат {chat_data['chat_id']} для пользователей {user1_id} и {user2_id}')

                delete_random_user(user1_id) 
                delete_random_user(user2_id) 

                user1_info = asyncio.run(userb.get_one(User.user_id == user1_id))
                user2_info = asyncio.run(userb.get_one(User.user_id == user2_id))

                if user1_info and user2_info:
                    asyncio.run(bot.send_message(chat_id=user1_id, text=f'Найден собеседник {markdown.hpre(user2_info.full_name)}. Ссылка на чат: {chat_data['invite_link']}'))
                    asyncio.run(bot.send_message(chat_id=user2_id, text=f'Найден собеседник {markdown.hpre(user1_info.full_name)}. Ссылка на чат: {chat_data['invite_link']}'))
                else:
                     logger.error(f'[Ошибка] Не удалось получить информацию о пользователях {user1_id} или {user2_id}')

                i += 2 
                continue
            else:
                logger.error(f'[Ошибка] Не удалось создать чат для {user1_id} и {user2_id}')

        i += 1 
    current_time = time.time()
    for user_id_str, user_info in list(data.items()):
        user_id = int(user_id_str)
        added_time = user_info.get('added_time', current_time)
        message_id = user_info.get('message_id')

        if current_time - added_time > 300 and message_id is None:
            try:
                message_obj = asyncio.run(bot.send_message(
                    chat_id=user_id,
                    text='Продолжить поиск?\n Если не ответите через 10 секунд, поиск будет остановлен.',
                    reply_markup=continue_search_button()
                ))
                data[user_id_str]['message_id'] = message_obj.message_id
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

    if user_id_str in data and data[user_id_str].get('message_id') == message_id:
        try:
            asyncio.run(bot.get_message(chat_id=user_id, message_id=message_id))
            logger.info(f'Поиск остановлен для пользователя {user_id} по таймауту.')
            asyncio.run(bot.edit_message_reply_markup(chat_id=user_id, message_id=message_id, reply_markup=None))
            delete_random_user(user_id)
            
        except Exception as e:
            logger.info(f'Пользователь {user_id} продолжил поиск.')
            data[user_id_str]['added_time'] = time.time()
            data[user_id_str]['message_id'] = None
            data[user_id_str]['data_activity'] = dateMSC
            random_users.redis_cashed(data=data, ex=None)

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(5.0, monitor_random_search.s(), name='monitor random search')
