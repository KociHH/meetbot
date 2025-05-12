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
from keyboards.reply_button import admin_command, man_woman, name_state, yes_no
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils import markdown
from utils.db_work import Update_date, noneuser
from keyboards.lists_command import admin_list, man_woman_list, save_or_change
from utils.db_work import __redis_room__, __redis_users__

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
async def start_(message: Message, state: FSMContext, db_session: AsyncSession):
    if message.from_user.is_bot:
        await message.answer('Вы бот')
        await asyncio.sleep(5)
        return
    elif message.from_user is None:
        await message.answer("Не удалось получить информацию о пользователе.")
        return
    
    username = message.from_user.username or "Не задано"
    full_name = message.from_user.full_name or "Аноним"
    user_id = message.from_user.id
    
    noneuser_None = await noneuser(
        message=message,
        state=state,
        user_id=user_id,
        user_name=username,
        db_session=db_session
        )
    if noneuser_None:
        await state.set_state(start_register.name)
        await state.update_data({
            "full_name": full_name
        })
        text = (
            f'{markdown.hblockquote("Регистрация")}\n\n'
            f'Чтобы пользователи знали кто им присылает сообщение можешь оставить {markdown.hbold(full_name)}\n'
            f'или ввеcти другой\n\n'
            f'Также можешь пропустить тогда твой никнейм будет: {markdown.hbold(anonim)}.\n'
            f'Также надо будет указать ваш пол'
        )
        await message.answer(text=text, reply_markup=name_state())


@router.message(F.text == name_state_bt.mine, StateFilter(start_register.name))
async def name_(message: Message, state: FSMContext):
    await state.set_state(start_register.name)
    await message.answer(text="Никнейм:", reply_markup=ReplyKeyboardRemove())
    
    
@router.message(StateFilter(start_register.name))
async def enter_name(message: Message, state: FSMContext):
    full_name = message.text
    if len(full_name) > 20:
        await message.answer('Никнейм слишком большой!\n введите снова...')
        asyncio.sleep(0.5)
        await name_(message, state)
    else:
        await state.update_data({'full_name': full_name})
        await state.set_state(start_register.enter)
    

@router.message(F.text == name_state_bt.leave, StateFilter(start_register.name))
async def sucsess(message: Message, state: FSMContext, db_session: AsyncSession):
    username = message.from_user.username
    user_id = message.from_user.id
    data = await state.get_data()
    full_name = data.get('full_name')
    gender = data.get('gender')
    
    await message.answer(text=f'Успешно применено! Твой никнейм: {full_name} ', reply_markup=ReplyKeyboardRemove())
    base = await db_session.scalar(select(User).where(User.user_id == user_id))
    logger.info('Пользователь успешно обновил свой никнейм')
    if base:
        update = Update_date(
            base=base, 
            params={
                "full_name": full_name,
                "gender": gender,
                }
            )
        update.update()
        await update.save_(db_session=db_session)

    else:
        user = User(user_id = user_id, username = username, full_name = full_name)
        db_session.add(user)
        await db_session.commit()
        logger.error('Пользователя нет в базе данных, добавление...')


@router.message(StateFilter(start_register.m))
async def checkname_(message: Message, state: FSMContext):
    data = await state.get_data()
    gender = data.get('gender')
    full_name = data.get('full_name')
    await state.update_data({"full_name": full_name})
    await state.set_state(start_register.check_name)
    await message.answer(
        f'{markdown.hbold('Вы уверены? Ваш пол и никнейм будут ⤵️')}\n\n {markdown.hbold("никнейм")}: {full_name}\n {markdown.hbold("пол")}: {gender}',
        reply_markup=yes_no()
    )


@router.message(StateFilter(start_register.enter))
async def gender_user(message: Message, state: FSMContext):
    await message.answer('Ваш пол:', reply_markup=man_woman())
    await state.set_state(start_register.gender)
        

@router.message(F.text.in_(man_woman_list), StateFilter(start_register.gender))
async def enter_gender_user(message: Message, state: FSMContext):
    gender = message.text
    await state.update_data({'gender': gender})
    await state.set_state(start_register.m)


@router.message(F.text == name_state_bt.skip, StateFilter(start_register.name))
async def skip(message: Message, state: FSMContext, db_session: AsyncSession):
    await state.update_data({'full_name': anonim})
    await sucsess(message, state, db_session)

    
@router.message(F.text.lower() == "да", StateFilter(start_register.check_name))
async def yes_state(message: Message, state: FSMContext, db_session: AsyncSession):
    await sucsess(message, state, db_session)


@router.message(F.text.lower() == "нет", StateFilter(start_register.check_name))
async def no_state(message: Message, state: FSMContext):
    await start_(message, state)
    

@router.message(F.text.in_(save_or_change), StateFilter(start_register.check_name))
async def save_change(message: Message, state: FSMContext, db_session: AsyncSession):
    text = message.text
    if text == yes_no_bt.yes:
        await sucsess(message, state, db_session)
    elif text == yes_no_bt.change_gender:
        await gender_user(message, state)
    elif text == yes_no_bt.change_nickname:
        await name_(message, state)