import asyncio
import logging
from re import U
from typing import Any, Dict
from aiogram import F, Bot, Router
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from commands.state import Admin_menu
from config import ADMIN_ID
from data.sqlchem import User
from keyboards.reply_button import AdminFuctional, back_bt
from keyboards.button_names import main_commands_bt, admin_command_bt, chats_bt, reply_back_bt
from keyboards.lists_command import admin_list, admin_panels_info
from utils.dataclass import BasicUser
from utils.db_work import __redis_room__, __redis_users__, __redis_random__
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
        await message.answer(text='Функционал:', reply_markup=AdminFuctional().admin_command())
        await state.set_state(Admin_menu.main)

@router.message(StateFilter(Admin_menu.main), F.text.in_(admin_list))
async def admin_command_(message: Message, state: FSMContext):
    text = message.text
    if text == admin_command_bt.users_active:
        data: dict = __redis_random__.get_cashed()
        await message.answer(
            f'Пользователей в поиске: {len(list(data.keys()))}',
            reply_markup=AdminFuctional().searching_users()
            )
        await state.set_state(Admin_menu.search_us_panel)
        
    elif text == admin_command_bt.rooms:
        data: dict = __redis_room__.get_cashed()
        await message.answer(
            f"Комнат: {len(list(data.keys()))}",
            reply_markup=AdminFuctional().rooms_all_info()
            )  
        await state.set_state(Admin_menu.rooms_panel)

@router.message(F.text.in_(admin_panels_info), StateFilter(Admin_menu.rooms_panel, Admin_menu.search_us_panel))
async def admin_panels_datas(message: Message, state: FSMContext):
    text = message.text
    if text == admin_command_bt.users_searching:
        data: dict = __redis_random__.get_cashed()
        users_count = len(data.keys())
        message_result = 'На данный момент нет ни кого в поиске.\n Прошу обновить информацию.'
        if users_count >= 1:
            user_ids = list(data.keys())
            message_result = 'Пользователи в поиске:\n' + '\n'.join(user_ids)
        await message.answer(message_result)
    
    if text == admin_command_bt.rooms_all_info:
        pass
    
    if text == reply_back_bt.back:
        await admin_panel(message, state)
        await state.clear()


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