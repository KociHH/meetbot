from email import message
import logging
import stat
from sqlalchemy import select
from commands.state import Main_menu, Menu_chats, find_groups, Admin_menu, random_user, Back
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils import markdown
from data.redis_instance import __redis_room__, __redis_users__, RAccess, users, random_users, room, redis_random, redis_random_waiting
from keyboards.lists_command import command_chats, main_command_list
from utils.db_work import create_private_group, find_func, ProgressBar
from utils.other import error_logger, import_functions, menu_chats, bot
from aiogram import F, Bot, Router
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from data.sqlchem import User
from keyboards.button_names import chats_bt, main_commands_bt, search_again_bt
from keyboards.reply_button import admin_command, chats, main_commands, back_bt
from sqlalchemy.ext.asyncio import AsyncSession
from utils.dataclass import BasicUser
from keyboards.inline_buttons import go_tolk
from utils.other import remove_invisible, kats_emodjes, count_meetings, RandomMeet
from data.utils import CreatingJson
from data.sql_instance import userb
from celery import Celery
from data.celery.tasks import create_private_group, search_random_partner, create_private_chat, remove_user_from_search, add_user_to_search

pseudonym = 'psdn.'
anonim = 'Anonim'
logger = logging.getLogger(__name__)
router = Router(__name__)

text_instructions = markdown.text(
    '/find - искать собеседника(ов)\n\n'
    "/stop - выйти из поиска\n\n"
    f'⏭️ {markdown.blockquote("После того как нашелся собеседник, бот вам отправит пригласительную ссылку в чат")}\n',
    )

@router.message(F.text.in_(command_chats), StateFilter(Menu_chats.system_chats))
async def system_chats(message: Message, state: FSMContext):
    text = message.text
    if text == chats_bt.one:
        await message.answer(
            text=
            f'Сейчас в поиске {users.search_online()}'
            f'Введите с каким кол-во участников хотите начать общение [мин от {markdown.hpre('3')}]'
        )
        await state.set_state(find_groups.enter_users)

    elif text == chats_bt.two:
        await message.answer(text=text_instructions, reply_markup=main_commands())
        await state.set_state(random_user.main)


@router.message(
    F.text.in_(main_command_list) or Command(commands=['find',  'stop'], prefix='/'),
    StateFilter(find_groups.main)
    )
async def reply_command(message: Message, state: FSMContext, db_session: AsyncSession):
    user_id = message.from_user.id
    text = message.text
    if text == main_commands_bt.find:
        chat = await create_private_group()
        chat_id = chat.id
        ff = await find_func(message, user_id, chat_id)
        if not ff:
            logger.info(f'Ошибка при поиске собеседника: {user_id} или Поиск уже идет')
            return False
            
    elif text == main_commands_bt.stop:
        data: list = users.redis_data()
        if user_id in data and data:
            data.remove(user_id)
            __redis_users__.cashed(key='active_users', data=data, ex=None)
            await message.answer(text='🛑 Вы прекратили поиск')
        else:
            await message.answer(text='🚀 Вы еще не в поиске нажмите скорее /find')
        
    elif text == main_commands_bt.back:
        await menu_chats(message, state)


@router.message(
    F.text.in_(main_command_list) or Command(commands=['find',  'stop'] or search_again_bt.search, prefix='/'),
    StateFilter(random_user.main, random_user.search_again)
    )
async def send_random_user(message: Message, state: FSMContext):
    user = BasicUser.from_message(message)
    text = message.text
    message_text = 'Начался поиск🔍'
    try:
        if not remove_invisible(user.full_name):
            await state.set_state(random_user.if_null)
            await message.answer(
                text=f'Я вижу у тебя невидимый никнейм. Прошу ввести свой псевдоним 📝',
                reply_markup=back_bt()
                )

        if text == main_commands_bt.find:
            add_user_to_search.delay(user.user_id, 'random_meet')
            
            await message.answer(message_text, reply_markup=ReplyKeyboardRemove())
            
        if text == main_commands_bt.stop:
            if remove_user_from_search.delay(user.user_id).get():
                logger.info(f'{user.user_id} вышел из поиска')
                await message.answer(
                    text='⛔️ Вы вышли из поиска.\n Нажмите /find чтобы возобновить поиск или на кнопки в панели ниже.',
                    reply_markup=main_commands()
                )
                await state.set_state(random_user.search_again)
        
        if text == main_commands_bt.back:
            await state.set_state(Back.main_menu)


    except Exception as e:
        logger.error(error_logger(False, 'send_random_user', e))


@router.message(F.text, StateFilter(random_user.if_null))
async def saved_name_user(message: Message, state: FSMContext):
    user = BasicUser.from_message(message)
    data = await state.get_data()
    text: str = data.get('name')
    if not text:
        text = message.text

    if not remove_invisible(text):
        await message.answer(f'Я виду что вы опять ввели невидимый никнейм, прошу повторить попытку снова 🔄')
        await state.set_state(random_user.again_name)

    save = await userb.update(User.user_id == user.user_id, {'pseudonym': text.join(f" {pseudonym}")})
    if save:
        await state.set_state(random_user.main)
        await message.answer(
            text=f'👌 Успешно сохранено.\n\n Ваш текущий псевдоним: {text}\n Теперь у вас есть доступ к поиску.',
            reply_markup=main_commands()
            )
    else:
        logger.info(f'[Ошибка] При сохранении псевдонима {text} юзера {user.user_id}, произошла ошибка')
        await message.answer(error_logger(True))

@router.message(F.text, StateFilter(random_user.again_name))
async def again_enter_name(message: Message, state: FSMContext):
    await state.set_data({'name': message.text})
    await state.set_state(random_user.if_null)

@router.message(F.text == main_commands_bt.back, StateFilter(Back.main_menu))
async def back_main_menu(message: Message, state: FSMContext):
    await menu_chats(message, state, edit=True)