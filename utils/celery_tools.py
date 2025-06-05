import logging
import random
import asyncio
from typing import Any
from aiogram.enums import ParseMode
from aiogram import Bot
from aiogram.types import Message
from config import BOT_TOKEN, BOT_ID
from aiogram.client.default import DefaultBotProperties
from data.redis_instance import redis_random, redis_random_waiting, __redis_random__, __redis_random_waiting__
from utils.other import error_logger
from kos_Htools.telethon_core import multi
from telethon.tl.functions.messages import AddChatUserRequest
from telethon.tl.functions.channels import EditAdminRequest
from telethon.tl.types import ChatAdminRights
from telethon import TelegramClient
from data.celery.tasks import add_user_to_search, remove_user_from_search, create_private_chat

logger = logging.getLogger(__name__)
# random_users = {user_id: {skip_users: [int], tolk_users: [int],"added_time": время_добавления, "message_id": id_сообщения_или_null, data_activity: datetime}}
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
title_chat = 'Чатик знакомств'

def random_search(users_data: list[str], data: dict) -> tuple[int, int] | None:
    size = len(users_data)
    if size < 2:
        return None

    random.shuffle(users_data)

    for i in range(size - 1):
        user1_id_str = users_data[i]
        user2_id_str = users_data[i+1]

        user1_data = data.get(user1_id_str, {})
        user2_data = data.get(user2_id_str, {})

        user1_id = int(user1_id_str)
        user2_id = int(user2_id_str)

        user1_exception = user1_data.get('exception', [])
        user2_exception = user2_data.get('exception', [])
        
        if user2_id not in user1_exception and \
           user1_id not in user2_exception:
            user1_exception.append(user2_id)
            user2_exception.append(user1_id)
            
            __redis_random__.cached(data=data, ex=None)
            return user1_id, user2_id
    
    logger.info(f'Нет подходящих юзеров для пар, в поиске: {size}')
    return None

def count_meetings() -> int:
    data = __redis_random_waiting__.get_cached(redis_random_waiting)
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

class RandomMeet:
    def __init__(self, user_id) -> None:
        self.user_id = user_id

    def getitem_to_random_user(self, item: str = None, change_to: str | int | None = None, _change_provided: bool = False, update_many: dict = None, data: dict | None = None):
        if not data:
            data: dict = __redis_random__.get_cached()
        if isinstance(self.user_id, int):
            self.user_id = str(self.user_id)
        
        if update_many:
            if self.user_id in data and isinstance(data.get(self.user_id), dict):
                user_data = data[self.user_id]
                for itm, val in update_many.items():
                    user_data[itm] = val
                __redis_random__.cached(data=data, ex=None)
                return data
            else:
                logger.error(f'Пользовательские данные не найдены или имеют неверный формат для {self.user_id} при попытке группового обновления.')
                return None       

        obj = data.get(self.user_id, {}).get(item, None)
        if self.user_id in data.keys():
            if _change_provided:
                if self.user_id in data and isinstance(data.get(self.user_id), dict):
                     data[self.user_id][item] = change_to
                     __redis_random__.cached(data=data, ex=None)
                else:
                     logger.error(f'Пользовательские данные не найдены или имеют неверный формат для {self.user_id} при попытке обновления {item}')
                return data.get(self.user_id, {}).get(item, None)
            else:
                if obj is not None:
                    return obj
                else:
                    logger.warning(f'Не найден объект: {item} |p.s {obj} для пользователя {self.user_id}')
                    return None

        else:
            logger.warning(f'Такого {self.user_id} нет в {redis_random}')
            return None

    def meeting_account(data: dict | None = None) -> int:
        if not data:
            data = __redis_random_waiting__.get_cached()
        rooms = sorted(data.keys())
        size = len(rooms)
        if size >= 1:
            for i in range(1, len(rooms)):
                if i not in rooms:
                    return i
        return 1

    def changes_to_random_waiting(self, field: str | int, value: Any | None = None):
        data = __redis_random_waiting__.get_cached()

        for room_id, room_info in data.items():
            users: dict = room_info.get('users', {})

            if self.user_id in users:
                users[self.user_id][field] = value
                __redis_random_waiting__.cached(data=data, ex=None)

                return room_id, True, users
        return None, False, None

    def delete_meet(count_meet: int):
        data = __redis_random_waiting__.get_cached(redis_random_waiting)
        data.pop(count_meet) if isinstance(data, dict) else logger.error(f'Не тот тип {type(data)}')
        __redis_random_waiting__.cached(data=data, ex=None)
        return data

    def delete_random_user(self):
        data = __redis_random__.get_cached(redis_random)
        data.pop(str(self.user_id), None)
        __redis_random__.cached(data=data, ex=None)


async def find_func(message: Message, user_id: int, chat_id: int | None) -> bool | None:
    try:
        if not add_user_to_search.delay(message.message_id, user_id, redis_random).get():
            await message.answer(text='⏳ Вы уже в очереди. Пожалуйста, подождите...')
            await asyncio.sleep(1)
            return False

        data = __redis_random__.get_cached(redis_random)
        partner_id = None
        user_data = data.get(str(user_id), {})
        skipped_users = user_data.get('skip_users', [])
        tolked_users = user_data.get('tolk_users', [])

        available_partners = [p_id for p_id in data.keys() if p_id.isdigit() and int(p_id) != user_id and int(p_id) not in skipped_users and int(p_id) not in tolked_users]

        if available_partners:
            partner_id_str = random.choice(available_partners)
            partner_id = int(partner_id_str)

        if partner_id and chat_id:
            chat = await message.bot.create_chat_invite_link(
                chat_id=chat_id,
                name=title_chat,
                member_limit=2,
            )
            
            if chat:
                await message.bot.send_message(
                    chat_id=user_id,
                    text=f"🔗 Собеседник найден! Войдите в чат:\n {chat.invite_link}"
                )
                await message.bot.send_message(
                    chat_id=partner_id,
                    text=f"🔗 Собеседник найден! Войдите в чат:\n {chat.invite_link}"
                )
                
                remove_user_from_search.delay(user_id)
                remove_user_from_search.delay(partner_id)
                
                room_data = create_private_chat.delay([user_id, partner_id], chat_id).get()
                if room_data:
                    logger.info(f'[Created]:\n {room_data}')
                    return True
                else:
                    await message.answer(error_logger(True))
                    logger.error(f'[Ошибка] при получении Json чата {chat_id}')
                    return False
                    
            else:
                logger.error(f'Чат не создался с ID: {chat_id}')
                return None
        return False
                    
    except Exception as e:
        logger.error(error_logger(False, 'find_func', e)) 
        return False


async def create_private_group() -> Any:
    try:
        client = await multi()
        await multi.get_or_switch_client(switch=True)

        group = await client.create_supergroup(
            title=title_chat,
            about="Только по приглашению",
            for_channel=False
        )
        logger.info(f'Группа создана с ID: {group.id}')

        await client.invoke(AddChatUserRequest(
            chat_id=group.id,
            user_id=BOT_ID,
        ))
        
        admin_rights = ChatAdminRights(
            post_messages=True,
            edit_messages=True,
            delete_messages=True,
            ban_users=True,
            invite_users=True,
            pin_messages=True,
            add_admins=True,
            anonymous=True,
            manage_call=True,
            other=True,
            manage_topics=True,
            change_info=True,
            create_invite=True,
            delete_chat=True,
            manage_chat=True,
            manage_video_chats=True,
            can_manage_voice_chats=True,
            can_manage_chat=True,
            can_manage_channel=True
        )
        
        admin_add = await client.invoke(EditAdminRequest(
            channel=group.id,
            user_id=BOT_ID,
            admin_rights=admin_rights,
            rank="caretaker"
        ))
        
        logger.info(f"Бот-администратор добавлен в группу {group.id} с правами администратора")   
        if group and admin_add:
            return group
        else:
            logger.error('[Ошибка] функция create_private_group не вернула группу')
            return None
        
    except Exception as e:
        logger.error(error_logger(False, 'create_private_group', e))
        return None