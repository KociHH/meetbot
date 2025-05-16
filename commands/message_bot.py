import logging
from sqlalchemy import select
from commands.state import Main_menu, Menu_chats, find_groups, Admin_menu, random_user
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
from keyboards.reply_button import admin_command, chats, main_commands
from sqlalchemy.ext.asyncio import AsyncSession
from utils.dataclass import BasicUser
from keyboards.inline_buttons import go_tolk
from utils.other import remove_invisible, kats_emodjes, count_meetings
from data.utils import CreatingJson


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
            __redis_users__.cashed(key='active_users', data=data, ex=0)
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
        if text == main_commands_bt.find:
            data = random_users.redis_data()
            random_users.redis_cashed(data.append[user.user_id])

            pb = ProgressBar(redis_random, message_id, chat_id, message_text, user.user_id)
            message_obj = await message.answer(message_text)
            chat_id = message_obj.chat.id
            message_id = message_obj.message_id
            

            data, partner_obj = await pb.search_random()
            partner_id = partner_obj.id
            partner_full_name = partner_obj.full_name
            users_party = [user.user_id, partner_id]
            # {num_meet: {users: {user_id: {skip_users: [int], tolk_users: [int], ready: bool}}}, created: datetime}
            save = random_users.redis_cashed(data, None)
            
            waiting_data = redis_random_waiting.redis_data()

            users_data = {}
            for us in users_party:
                new_data = waiting_data.get('users', {}).get(us, {})
                if new_data:
                    users_data[us] = {
                        'skip_users': new_data.get('skip_users', 1),
                        'tolk_users': new_data.get('tolk_users', 1)
                    }

            if len(users_data) == 2:
                new_data = CreatingJson.random_waiting({'users': users_data}, count_meetings())
            else:
                logger.error(f'[Ошибка] Недостаточно данных для обоих пользователей: {users_data}')
                return False

            if save and new_data:
                for user_ids, names in users_party, [user.full_name, partner_full_name]:
                    names = remove_invisible(names)
                    clarification = f'{markdown.hblockquote(f'Если эмоджи котиков значит у этого человека [{markdown.hbold('Невидимый никнейм')}]')}',
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    await bot.send_message(
                        text=
                        f'Начать общение с {names if names.strip() else {kats_emodjes()}}?\n\n {clarification}',
                        chat_id=user_ids,
                        reply_markup=go_tolk()
                    )
            else:
                logger.error('[Ошибка] не изменились Redis данные random_users')
                return False
        
        if text == main_commands_bt.stop:
            data = random_users.redis_data()
            if data:
                data.remove(user.user_id)
                random_users.redis_cashed(data=data, ex=None)
                logger.info(f'{user.user_id} вышел из поиска')
                await message.answer(
                    text='⛔️ Вы вышли из поиска.\n Нажмите /find чтобы возобновить поиск или на кнопки в панели ниже.',
                    reply_markup=main_commands()
                    )
                await state.set_state(random_user.search_again)

    except Exception as e:
        logger.error(error_logger(False, 'send_random_user', e))



