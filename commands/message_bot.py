from email import message
import logging
import stat
from kos_Htools import BaseDAO
from sqlalchemy import select
from commands.state import Main_menu, Menu_chats, find_groups, Admin_menu, random_user, Back
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils import markdown
from data.redis_instance import __redis_room__, __redis_users__, redis_random, redis_users, __redis_random__
from keyboards.lists_command import command_chats, main_command_list
from aiogram import F, Bot, Router
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from data.sqlchem import User
from keyboards.button_names import chats_bt, main_commands_bt, search_again_bt
from keyboards.reply_button import chats, main_commands, back_bt
from sqlalchemy.ext.asyncio import AsyncSession
from utils.dataclass import BasicUser
from keyboards.inline_buttons import go_tolk
from data.utils import CreatingJson
from data.celery.tasks import message_text, remove_user_from_search, add_user_to_search, monitor_search_users_party
from utils.celery_tools import bot, RandomMeet, create_private_group, find_func

pseudonym = 'psdn.'
anonim = 'Anonim'
logger = logging.getLogger(__name__)
router = Router(name=__name__)

text_instructions = markdown.text(
    f'{main_commands_bt.find} - искать собеседника(ов) (от вашего выбора)\n\n'
    f"{main_commands_bt.stop} - выйти из поиска\n\n"
    f'⏭️ {markdown.blockquote("После того как нашелся собеседник, бот вам отправит пригласительную ссылку в чат")}\n',
    )

@router.message(F.text.in_(command_chats), StateFilter(Menu_chats.system_chats))
async def system_chats(message: Message, state: FSMContext):
    text = message.text
    if text == chats_bt.one:
        await message.answer(
            text=
            f'Сейчас в поиске {len(__redis_users__.get_cached())}'
            f'Введите с каким кол-во участников хотите начать общение [мин от {markdown.hcode('3')}]'
        )
        await state.set_state(find_groups.enter_users)

    elif text == chats_bt.two:
        await message.answer(text=text_instructions, reply_markup=main_commands())
        await state.set_state(random_user.main)


@router.message(
    F.text.in_(main_command_list),
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
        data: list = __redis_users__.get_cached(redis_users)
        if user_id in data and data:
            data.remove(user_id)
            __redis_users__.cashed(redis_users, data=data, ex=None)
            await message.answer(text='🛑 Вы прекратили поиск')
        else:
            await message.answer(text='🚀 Вы еще не в поиске нажмите скорее /find')
        
    elif text == main_commands_bt.back:
        from utils.other import menu_chats
        await menu_chats(message, state)


@router.message(
    F.text.in_(main_command_list),
    StateFilter(random_user.main, random_user.search_again)
    )
async def send_random_user(message: Message, state: FSMContext, db_session: AsyncSession):
    user = BasicUser.from_message(message)
    text = message.text
    rm = RandomMeet(user.user_id)
    rm.getitem_to_random_user(item='contine_id', change_to=None, _change_provided=True)
    try:
        from utils.other import remove_invisible
        if not remove_invisible(user.full_name):
            await state.set_state(random_user.if_null)
            await message.answer(
                text=f'Я вижу у тебя невидимый никнейм. Прошу ввести свой псевдоним 📝',
                reply_markup=back_bt()
                )

        if text == main_commands_bt.find:
            message_count = rm.getitem_to_random_user(item='message_id')
            if not message_count:
                message_count = 0
                
            if message_count >= 5:
                await message.answer(
                    text=
                    f'‼️ Вы превысили лимит не решенных сообщений. {message_count}/5\n'
                    f'Дальнейший поиск был {markdown.hcode("остановлен")}, нажмите на (😒 скип) или (✅ общаться)\n'
                    f'Пожалуйста ответьте на каждое из сообщений, чтобы продолжить {markdown.hcode("поиск")}'
                )
            message_obj = await message.answer(message_text) 
            change = rm.getitem_to_random_user(item='message_id', change_to=message_count + 1)
            if change:
                add_user_to_search.delay(message_obj.message_id, user.user_id, redis_random)
                monitor_search_users_party.delay()
            else:
                logger.error('[Ошибка] не произошло изменение message_count на + 1')
                from utils.other import error_logger
                await bot.send_message(chat_id=user.user_id, text=error_logger(True))

        if text == main_commands_bt.stop:
            if remove_user_from_search.delay(user.user_id).get():
                logger.info(f'{user.user_id} вышел из поиска')
                await message.answer(
                    text='⛔️ Вы вышли из поиска.\n 🔄 Чтобы возобновить поиск нажмите на кнопку ниже.',
                    reply_markup=main_commands()
                )
                await state.set_state(random_user.search_again)
        
        if text == main_commands_bt.back:
            await state.set_state(Back.main_menu)


    except Exception as e:
        from utils.other import error_logger
        logger.error(error_logger(False, 'send_random_user', e))


@router.message(F.text, StateFilter(random_user.if_null))
async def saved_name_user(message: Message, state: FSMContext, db_session: AsyncSession):
    user = BasicUser.from_message(message)
    data = await state.get_data()
    text: str = data.get('name')
    userb = BaseDAO(User, db_session)
    if not text:
        text = message.text

    from utils.other import remove_invisible
    if not remove_invisible(text):
        await message.answer(f'Я вижу что вы опять ввели невидимый никнейм, прошу повторить попытку снова 🔄')
        await state.set_state(random_user.again_name)

    save = await userb.update(User.user_id == user.user_id, {'pseudonym': text.join(f" {pseudonym}")})
    if save:
        await state.set_state(random_user.main)
        await message.answer(
            text=f'👌 Успешно сохранено.\n\n Ваш текущий псевдоним: {text}\n Теперь у вас есть доступ к поиску.',
            reply_markup=main_commands()
            )
    else:
        logger.info(f'При сохранении псевдонима {text} юзера {user.user_id}, произошла ошибка')
        from utils.other import error_logger
        await message.answer(error_logger(True))

@router.message(F.text, StateFilter(random_user.again_name))
async def again_enter_name(message: Message, state: FSMContext):
    await state.set_data({'name': message.text})
    await state.set_state(random_user.if_null)

@router.message(F.text == main_commands_bt.back, StateFilter(Back.main_menu))
async def back_main_menu(message: Message, state: FSMContext):
    from utils.other import menu_chats
    await menu_chats(message, state, edit=True)

