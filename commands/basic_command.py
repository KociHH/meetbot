import asyncio
import logging
from typing import Any, Dict
from aiogram import F, Bot, Router
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from commands import message_bot
from commands.state import Admin_menu, start_register
from config import ADMIN_ID
from data.sqlchem import User
from keyboards.button_names import name_state_bt, yes_no_bt
from keyboards.reply_button import admin_command
from keyboards.lists_command import admin_list, man_woman_list, save_or_change
from utils.db_work import __redis_room__, __redis_users__
from utils.other import menu_chats

logger = logging.getLogger(__name__)
router = Router(name=__name__)
anonim = 'Anonim'


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
async def starting(message: Message, state: FSMContext):
    await menu_chats(message, stae=state)