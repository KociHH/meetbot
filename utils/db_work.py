import re
from utils.other import import_functions
import asyncio
from aiogram.types import Message
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from data.sqlchem import User
import logging
from aiogram.fsm.context import FSMContext
import random
from data.redis_instance import __redis_room__, __redis_users__
from utils.date_time_moscow import date_moscow
from config import ADMIN_ID
from kos_Htools.telethon_core import multi
from telethon.tl.functions.messages import AddChatUserRequest
from telethon.tl.functions.channels import EditAdminRequest
from telethon.tl.types import ChatAdminRights
from telethon import TelegramClient
from kos_Htools.sql.sql_alchemy import BaseDAO

logger = logging.getLogger(__name__)
set_users_active = set()
list_ids_message = []


async def noneuser(
        message: Message,
        state: FSMContext,
        user_id: int,
        db_session: AsyncSession,
        user_name: str | None = None
        ) -> bool:
    try:
        dao = BaseDAO(User, db_session)
    
        if user_name is None:
            user_name = 'Не задано'

        if user_id == ADMIN_ID:
            admin_status = 'admin'
        else:
            admin_status = 'user'

        if not await dao.get_one(User.user_id == user_id):
            await dao.create(
                data={
                    'user_id': user_id,
                    'user_name': user_name,
                    'admin_status': admin_status            
                }
            )
            return True
        else:
            await dao.update(
                User.user_id == user_id,
                data={
                    'user_id': user_id,
                    'user_name': user_name,                
                    }  
                )
            await import_functions(x='menu_chats', message=message, state=state, db_session=db_session)
            return False
        
    except Exception as e:
        logger.error(f'Ошибка в noneuser: {e}')
        return True


async def time_event_user(event) -> bool:
    try:
        await asyncio.sleep(300)
        
        chat = await event.get_chat()
        if not chat:
            logger.error("Не удалось получить информацию о чате")
            return False
            
        participants = await event.client.get_participants(chat)
        
        data = __redis_room__.get_cashed()
        chat_data = data.get(f'room-{chat.id}')
        
        if not chat_data:
            logger.error("Не найдены данные чата в Redis")
            return False
            
        expected_users = chat_data.get('users', []) 
        joined_users = [p.id for p in participants if not p.bot]
        
        if len(joined_users) < 2:
            logger.warning(f"Не все пользователи присоединились к чату {chat.id}")
            logger.info(f"Ожидаемые пользователи: {expected_users}")
            logger.info(f"Присоединившиеся пользователи: {joined_users}")
            return False
            
        if not all(user_id in joined_users for user_id in expected_users):
            logger.warning(f"Присоединились не те пользователи, которые ожидались")
            return False
            
        logger.info(f"Все пользователи успешно присоединились к чату {chat.id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при проверке времени входа: {e}")
        return False


async def find_func(message: Message, user_id: int, chat_id: int | None) -> bool | None:
    global list_ids_message
    gett = __redis_users__.get_cashed()
    try:
        title = 'Anonim chat'
        if user_id in set_users_active:
            await message.answer(text='⏳ Вы уже в очереди. Пожалуйста, подождите...')
            await asyncio.sleep(1)
            return False
        
        set_users_active.add(user_id)   
        __redis_users__.cashed(key='active_users', data=list(set_users_active), ex=0) 
        if len(gett) > 1:
            partner_id = random.choice([int(partner) for partner in gett if user_id != partner])
            
            if partner_id and chat_id:
                chat = await message.bot.create_chat_invite_link(
                    chat_id=chat_id,
                    name=title,
                    member_limit=2,
                    )
                
                message_id = message.message_id
                chat_message_id = message.chat.id
                list_ids_message = [message_id, chat_message_id]

            if chat:
                for partner in [user_id, partner_id]:
                    await asyncio.sleep(0.5)
                    await message.bot.send_message(
                        chat_id=partner,
                        text=f"🔗 Собеседник найден! Войдите в чат: {chat.invite_link}"
                    )
                set_users_active.discard(user_id)
                set_users_active.discard(partner_id)
                __redis_users__.cashed(key='active_users', data=list(set_users_active), ex=0) 
                __redis_room__.generate_json_duo(chat_id=chat_id, key='rooms')
                return True
                    
            else:
                logger.error(f'Чат не создался с ID: {chat_id}')
                return
        return False
                    
    except Exception as e:
        logger.error(f"Проблема в функции find_func {e}") 
        return False


async def create_private_group() -> Any:
    try:
        client = await multi.start_clients()
        if not client or not multi.bot_client:
            logger.error("Не удалось получить клиент или бота Telethon")
            return None

        group = await client.create_supergroup(
            title="Анонимный чат",
            about="Только по приглашению",
            for_channel=True
        )
        logger.info(f'Группа создана с ID: {group.id}')

        bot_id = await multi.bot_client.get_me()
        await client.invoke(AddChatUserRequest(
            chat_id=group.id,
            user_id=bot_id.id,
            fwd_limit=100
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
        
        pups = await client.invoke(EditAdminRequest(
            channel=group,
            user_id=bot_id.id,
            admin_rights=admin_rights,
            rank="Boss"
        ))
        
        logger.info(f"Бот-администратор добавлен в группу {group.id} с правами администратора")   
        if group and pups:
            return group
        else:
            logger.error('Ошибка: функция create_private_group не вернула группу')
            return None
        
    except Exception as e:
        logger.error(f"Ошибка при создании группы или добавлении бота: {e}")
        return None


async def delete_chat_after_timeout(message: Message, chat_id: int, data_room: dict, client: TelegramClient):
    try:
        await multi.start_clients()
        await asyncio.sleep(300)
        
        if len(data_room['users']) != 2:
            success = await message.bot.send_message(chat_id=chat_id, text=f'❌ Собеседник не присоединился за отведенное время,\n {chat_id} чат будет удален.')
            if success:
                await client.delete_dialog(chat_id)
                logger.info(f"Чат {chat_id} удален из-за отсутствия второго участника")
            else:
                logger.error(f"Ошибка при удалении чата после таймаута: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка при удалении чата после таймаута: {e}")
    