import logging
import random
import asyncio
from typing import Any
from aiogram.enums import ParseMode
from aiogram import Bot
from aiogram.types import Message
from kos_Htools import BaseDAO
from config import BOT_TOKEN, BOT_ID
from aiogram.client.default import DefaultBotProperties
from data.redis_instance import redis_random, redis_random_waiting, __redis_random__, __redis_random_waiting__
from data.sqlchem import User
from utils.other import error_logger
from kos_Htools.telethon_core import multi
from telethon.tl.functions.messages import AddChatUserRequest
from telethon.tl.functions.channels import EditAdminRequest
from telethon.tl.types import ChatAdminRights
from utils.time import time_for_redis
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
# random_users = {user_id: {skip_users: [int], tolk_users: [int],"added_time": время_добавления, "message_id": id_сообщения_или_null, data_activity: datetime}}
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
title_chat = 'Чатик знакомств'

async def details_fromDB(db_session: AsyncSession, users: list[int], name_or_pseudonym: bool = False) -> dict:
    data = {}
    userb = BaseDAO(User, db_session)
    try:
        for user_id in users:
            user_inf = await userb.get_one(User.user_id == user_id)
            if user_inf:
                name = user_inf.pseudonym if name_or_pseudonym and user_inf.pseudonym else user_inf.full_name
                data[user_id] = {
                    'user_inf': user_inf,
                    'name_or_pseudonym': name,
                    }
            else:
                logger.warning(f'Нет {user_id} в базе User')
                
    except Exception as e:
        logger.error(f'В функции details_fromDB: {e}')
    return data


def random_search(users_data: list[str], data: dict) -> tuple[int, int] | None:
    size = len(users_data)
    logger.debug(f"[random_search] Initial users_data: {users_data}, size: {size}")

    if size < 2:
        logger.info(f'Мало юзеров кто ведет поиск: {size}')
        return None

    random.shuffle(users_data)

    for i in range(size):
        user1_id_str = users_data[i]

        user1_exception: list = data[user1_id_str].get('exception', [])

        users_potential_partners = [
            uid for uid in users_data
            if uid != user1_id_str and uid not in user1_exception
        ]

        if users_potential_partners:
            for uid2 in users_potential_partners:
                user2_exception: list = data[uid2].get('exception', [])
                if user1_id_str not in user2_exception:
                    user1_exception.append(uid2)
                    user2_exception.append(user1_id_str)
                    data[user1_id_str]['exception'] = user1_exception
                    data[uid2]['exception'] = user2_exception
                    
                    __redis_random__.cached(data=data, ex=None)     
                    return int(user1_id_str), int(uid2)
                else:
                    continue
        else:
            continue
        
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
    def __init__(self, user_id: str | int) -> None:
        if isinstance(user_id, int):
            self.user_id = str(user_id)
        elif isinstance(user_id, str) and user_id.isdigit():
            self.user_id = user_id
        else:
            logger.error(f'Нечисловое user_id в методе RandomMeet: {user_id}')
            self.user_id = None

    def getitem_to_random_user(
            self,
            item: str = None,
            change_to: str | int | None = None,
            _change_provided: bool = False,
            update_many: dict = None,
            data: dict | None = None
        ):
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

    @staticmethod
    def meeting_account(data: dict | None = None) -> int:
        if not data:
            data = __redis_random_waiting__.get_cached()

        try:
            current_room_numbers = sorted(int(k) for k in data.keys() if str(k).isdigit())
        except ValueError:
            logger.error("Нецелые ключи найдены в данных random_waiting. Используется 1 по умолчанию")
            return 1

        if not current_room_numbers:
            return 1

        expected_room_number = 1
        for room_num in current_room_numbers:
            if room_num == expected_room_number:
                expected_room_number += 1
            elif room_num > expected_room_number:
                return expected_room_number
            
        return expected_room_number

    def getitem_to_random_waiting(
            self,
            field: str | int = None,
            value: Any | None = None,
            complete_update: bool = False,
            return_value: bool = False,
            return_full_info: bool = False,
            data: Any | None = None,
        ):
        if not data:
            data: dict = __redis_random_waiting__.get_cached()

        for room_id, room_info in data.items():
            users: dict = room_info.get('users', {})
            #  "2": {"users": {"7593814197": {"ready": false, "message_id": null}, "5537454918": {"ready": false, "message_id": null}}, "created": "2025-06-08T00:42:00+03:00"}"
            user_id_str = str(self.user_id)
            if user_id_str in users.keys():
                if return_full_info:
                    return room_id, users, room_info

                if return_value:
                    return users[user_id_str][field]
                
                if complete_update:
                    users[user_id_str][field] = value
                __redis_random_waiting__.cached(data=data, ex=None)

                return room_id, True, users
        return None, False, None

    @staticmethod
    def delete_meet(count_meet: int):
        data = __redis_random_waiting__.get_cached()
        data.pop(count_meet) if isinstance(data, dict) else logger.error(f'Не тот тип {type(data)}')
        __redis_random_waiting__.cached(data=data, ex=None)
        return data

    def delete_random_user(self):
        data = __redis_random__.get_cached()
        data.pop(str(self.user_id), None)
        __redis_random__.cached(data=data, ex=None)

    def reset_rdata(self, items: list[str], add: dict = None):
        data: dict = __redis_random__.get_cached()
        for ite in items:
            data[self.user_id][ite] = None
        if add:
            for key, value in add.items():
                data[self.user_id][key] = value

        print(f'Обнуленны данные {items} с помощью reset_rdata')
        __redis_random__.cached(data=data, ex=None)
        return data


async def find_func(message: Message, user_id: int, chat_id: int | None) -> bool | None:
    from data.celery.tasks import add_user_to_search, remove_user_from_search, create_private_chat
    try:
        if not add_user_to_search.delay(message.message_id, user_id, redis_random).get():
            await message.answer(text='⏳ Вы уже в очереди. Пожалуйста, подождите...')
            await asyncio.sleep(1)
            return None

        data = __redis_random__.get_cached(redis_random)
        partner_id = None

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
                    return None
                else:
                    await message.answer(error_logger(True))
                    logger.error(f'[Ошибка] при получении Json чата {chat_id}')
                    return None
                    
            else:
                logger.error(f'Чат не создался с ID: {chat_id}')
                return None
        return False
                    
    except Exception as e:
        logger.error(error_logger(False, 'find_func', e)) 
        return None


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
    

