import asyncio
import logging
from re import U
from typing import Any, Dict
from aiogram import F, Bot, Router
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from commands.state import Admin_menu, Menu_chats
from config import ADMIN_ID, BOT_TOKEN
from data.sqlchem import User
from keyboards.reply_button import AdminFuctional, back_bt, chats
from keyboards.button_names import main_commands_bt, admin_command_bt, chats_bt, reply_back_bt
from keyboards.lists_command import admin_list, admin_panels_info
from utils.dataclass import BasicUser
from utils.other import error_logger
from kos_Htools.sql.sql_alchemy import BaseDAO
from sqlalchemy.ext.asyncio import AsyncSession
from utils.time import dateMSC
from data.redis_instance import __redis_room__, __redis_users__, __redis_random__
from kos_Htools.telethon_core import multi
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils import markdown

logger = logging.getLogger(__name__)
router = Router(name=__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

hello_text = markdown.text(
    f'Привет\n'
    f'Этот бот предназначен для быстрых знакомств 💝\n'
    f'{markdown.hbold("Есть варианты:")}\n\n'
    f'{chats_bt.one}:\n Бот вам присылает приглашение в чат, вы вступаете в него и собеседники и вы общаетесь от 3х человек и больше\n\n'
    f'{chats_bt.two}:\n Бот вам присылает {markdown.hcode("имя")} собеседника если вы согласны и ваш собеседник то вы и ваш партнер получаете {markdown.hcode('@username')} друг друга\n' 
)

async def menu_chats(message: Message, state: FSMContext, edit: bool = False):
    if edit:
        try:
            await message.edit_text(
                text=f"{hello_text}",
                reply_markup=None
            )
        except Exception as e:
            logger.error(f"Не удалось отредактировать сообщение при возврате в меню: {e}")
        await message.answer(
            text=f"{hello_text}",
            reply_markup=chats()
        )
    else:
        await message.answer(
            text=f"{hello_text}",
            reply_markup=chats()
        )
    await state.set_state(Menu_chats.system_chats)


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
        await menu_chats(message, state)

    except Exception as e:
        error_logger(True)
        logger.warning(error_logger(False, 'starting', e))
    return
