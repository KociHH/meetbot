import re
from utils.other import error_logger, menu_chats
import asyncio
from aiogram.types import Message
from typing import Any
import random
from data.redis_instance import __redis_room__, __redis_users__, redis_random, redis_room, __redis_random__
from utils.time import dateMSC
from config import ADMIN_ID
from kos_Htools.telethon_core import multi
from telethon.tl.functions.messages import AddChatUserRequest
from telethon.tl.functions.channels import EditAdminRequest
from telethon.tl.types import ChatAdminRights
from telethon import TelegramClient
import logging
from config import BOT_ID
import random
from utils.other import bot
from data.celery.tasks import  add_user_to_search,  remove_user_from_search, create_private_chat


logger = logging.getLogger(__name__)
title_chat = 'Чатик знакомств'

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