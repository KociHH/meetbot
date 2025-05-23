import asyncio
import logging
from typing import Any, Dict
from aiogram import F, Bot, Router
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from commands.state import Admin_menu
from config import ADMIN_ID
from data.sqlchem import User
from keyboards.reply_button import admin_command
from keyboards.lists_command import admin_list
from utils.dataclass import BasicUser
from utils.db_work import __redis_room__, __redis_users__
from utils.other import error_logger, menu_chats
from kos_Htools.sql.sql_alchemy import BaseDAO
from sqlalchemy.ext.asyncio import AsyncSession
from utils.time import dateMSC

logger = logging.getLogger(__name__)
router = Router(name=__name__)

@router.message(Command('admin', prefix='/'))
async def admin_panel(message: Message, state: FSMContext):
    admin_id = message.from_user.id
    if admin_id in ADMIN_ID:
        await message.answer(text='Функционал:', reply_markup=admin_command())
        await state.set_state(Admin_menu.main)

        
@router.message(StateFilter(Admin_menu.main), F.text.in_(admin_list))
async def admin_command_(message: Message, state: FSMContext):
    list_count_room = []
    text = message.text
    if text == 'Кол-во пользователей в поиске':
        data = __redis_users__.get_cashed()
        await message.answer(f'Пользователей в поиске: {len(data)}')
        
    elif text == 'Кол-во комнат':
        data = __redis_room__.get_cashed()
        for enum in data.keys():
            list_count_room.append(enum)
        await message.answer(f"Комнат: {len(list_count_room)}")  

@router.message(Command('start', prefix='/'))
async def starting(message: Message, state: FSMContext, db_session: AsyncSession):
    try:
        user_obj = BasicUser.from_message(message)
        daouser = BaseDAO(User, db_session)
        where_user = User.user_id == user_obj.user_id

        user_id = user_obj.user_id
        full_name = user_obj.full_name

        admin_status = 'user'
        if user_id in ADMIN_ID:
            admin_status = 'admin'

        if await daouser.get_one(where_user):
            await daouser.update(
                where_user,
                {
                    'admin_status': admin_status,
                    'full_name': full_name,
                    'last_activity': dateMSC.replace(tzinfo=None)
                }
            )
        else:
            await daouser.create(
                {
                    'user_id': user_id,
                    'full_name': full_name,
                    'admin_status': admin_status,
                    'last_activity': dateMSC.replace(tzinfo=None)
                }
            )
    except Exception as e:
        error_logger(True)
        logger.warning(error_logger(False, 'starting', e))
    await menu_chats(message, state)