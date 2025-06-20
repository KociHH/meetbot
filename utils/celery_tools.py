import logging
import random
import asyncio
from typing import Any
from aiogram.enums import ParseMode
from aiogram import Bot
from aiogram.types import Message
from kos_Htools import BaseDAO
from config import BOT_TOKEN, BOT_ID, BOT_USERNAME
from aiogram.client.default import DefaultBotProperties
from data.redis_instance import(
    redis_random,
    redis_random_waiting, 
    __redis_random__, 
    __redis_random_waiting__,
    __redis_room__,
    redis_room,
    __redis_users__,
    __queue_for_chat__
    )
from data.sqlchem import PrivateChats, User
from utils.other import error_logger, about_groups
from kos_Htools.telethon_core import multi
from telethon.errors import ChatAdminRequiredError, FloodWaitError, UserIdInvalidError, RPCError, UsernameNotModifiedError
from telethon.tl.functions.messages import AddChatUserRequest, CreateChatRequest, MigrateChatRequest, ExportChatInviteRequest
from telethon.tl.functions.channels import EditAdminRequest, InviteToChannelRequest, UpdateUsernameRequest, CreateChannelRequest
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


class RandomGroupMeet:
    def __init__(self, add_users: list[int] | None, user: str | int | None) -> None:
        self.add_users = add_users
        if isinstance(user, int):
            self.user = user
        elif isinstance(user, str) and user.isdigit():
            self.user = int(user)
        else:
            self.user = None

    async def create_private_group(self, group_title: str):
        try:
            await multi()
            client = await multi.get_or_switch_client(switch=True)
            bot = await client.get_entity(BOT_USERNAME)
            result = await client(CreateChannelRequest(
                title=group_title,
                about=about_groups,
                megagroup=True
            ))
            updates = result.updates
            chat = None

            for update in updates:
                if hasattr(update, 'channel_id'):
                    chat_id = update.channel_id
                    chat = await client.get_entity(chat_id)
                    break
            if not chat:
                raise Exception("Не удалось получить chat_id созданной супергруппы")

            logger.info(f"Успешно создан чат под id: {chat_id}")    
            chat = await client.get_entity(chat_id)

            try:
                await client(UpdateUsernameRequest(
                    channel=chat,
                    username=''
                ))
            except UsernameNotModifiedError:
                pass

            await client(InviteToChannelRequest(
                channel=chat,
                users=[bot]
            ))

            admin_rights = ChatAdminRights(
                add_admins=True,
                invite_users=True,
                change_info=True,
                ban_users=True,
                delete_messages=True,
                pin_messages=True,
                manage_call=True,
                anonymous=False,
            )

            try:
                await client(EditAdminRequest(
                    channel=chat,
                    user_id=bot,
                    admin_rights=admin_rights,
                    rank='admin'
                ))
            # log
            except ChatAdminRequiredError:
                logger.error("Ошибка: недостаточно прав для назначения администратора боту.")
                raise
            except FloodWaitError as e:
                logger.error(f"Ошибка: превышен лимит запросов. Нужно подождать {e.seconds} секунд.")
                raise
            except UserIdInvalidError:
                logger.error("Ошибка: неверный user_id для бота.")
                raise
            except RPCError as e:
                logger.error(f"RPC ошибка: {e}")
                raise

            invite = await client(ExportChatInviteRequest(
                peer=chat
            ))
            invite_link = invite.link
            logger.info(f"Ссылка для приглашения: {invite_link}")
            return chat_id, invite_link

        except Exception as e:
            logger.error(f"Ошибка при создании приватной группы: {e}")
            raise
    

async def order_count(
        base: str | None = None, 
        base_db: str | None = None,
        data: dict | None = None, 
        db_session: AsyncSession | None = None,
        ) -> int | None:
    
    if base_db == "PrivateChats" and db_session and not data:
        chatb = BaseDAO(PrivateChats, db_session)
        all_chats_id: list = await chatb.get_all_column_values(PrivateChats.chat_id)
        expected_room_number = len(all_chats_id) + 1

    else:
        if base:
            if not data:
                db = None
                if base == redis_random_waiting:
                    db = __redis_random_waiting__
                elif base == redis_room:
                    db = __redis_room__
                else:
                    logger.error(f'Нет {base} ключа в redis')
                    return 0
            data: dict = db.get_cached()
        else:
            logger.error(f'Не передан аргументь base в функции order_count: {base}')
            return 0

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