import asyncio
import logging
from aiogram import F, Bot, Router
from aiogram.types import Message, ReplyKeyboardRemove, BufferedInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from commands.state import Admin_menu, Menu_chats
from config import ADMIN_ID, BOSS_ID, BOT_ID, BOT_TOKEN, BOT_USERNAME
from data.sqlchem import PrivateChats, SearchUser, User
from keyboards.reply_button import AdminFuctional, back_bt, chats
from keyboards.button_names import main_commands_bt, admin_command_bt, chats_bt, reply_back_bt, empty_bt
from keyboards.lists_command import admin_list, many_kds, party_kds
from utils.celery_tools import RandomGroupMeet
from utils.dataclass import BasicUser
from utils.other import error_logger, samples_log, group_title
from kos_Htools.sql.sql_alchemy import BaseDAO
from sqlalchemy.ext.asyncio import AsyncSession
from utils.time import dateMSC
from data.redis_instance import __redis_room__, __redis_users__, __redis_random__, __redis_random_waiting__
from kos_Htools.telethon_core import multi
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils import markdown
from config import PHONE_NUMBER

maximum_chats = 10
logger = logging.getLogger(__name__)
router = Router(name=__name__)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
hello_text = markdown.text(
    f'Привет\n'
    f'Этот бот предназначен для быстрых знакомств 💝\n'
    f'{markdown.hbold("Есть варианты:")}\n\n'
    f'{chats_bt.one}:\n'
    f"{markdown.hbold('Информация:')}\n"
    f'Бот вам присылает приглашение в чат, вы вступаете в него и ваши собеседники и общаетесь, для выбора строго от {markdown.hcode("5")} человек и больше.\n\n'
    f"{markdown.hbold('Примечания:')}\n"
    f'{markdown.hblockquote(
        "+ Для доступа к следующему поиску вам надо выйти с чата, ссылку на который вам присылал бот.\n"
        "  Отправьте команду /current_chat, чтобы найти на какой чат была отправленна ссылка.\n\n"
        "+ Если чат не будет активен (целые сутки), будет вынужденно удаление участников и чистка чата.\n"
        )} \n\n'

    f'{chats_bt.two}:\n'
    f"{markdown.hbold('Информация:')}\n"
    "После того как нашелся собеседник, вам и вашему партнеру бот отправит предложение «общаться либо нет» .\n"
    "Если вы и ваш собеседник будете согласны на общение, бот пришлет вам ссылку на профиль партнера.\n\n"
)

async def admin_back_check(text: str, state: FSMContext, message: Message, block: str):
    if text == reply_back_bt.back:
        await admin_command_(message, state, block=block)
        return True
    return

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
        await message.answer(text='🕹 Панель администрирования', reply_markup=AdminFuctional().root())
        await state.set_state(Admin_menu.main)

@router.message(StateFilter(Admin_menu.main), F.text.in_(admin_list))
async def admin_command_(message: Message, state: FSMContext, block: str | None = None):
    text = message.text
    if text == admin_command_bt.root.party or block == "party":
        await message.answer(
            text="Выберите действие:",
            reply_markup=AdminFuctional().party_from()
        )
        await state.set_state(Admin_menu.rparty)
        
    elif text == admin_command_bt.root.many or block == "many":
        await message.answer(
            text="Выберите действие:",
            reply_markup=AdminFuctional().many_from()
        )
        await state.set_state(Admin_menu.rmany)

@router.message(F.text.in_(party_kds), StateFilter(Admin_menu.rparty))
async def patry_panel(message: Message, state: FSMContext):
    text = message.text
    p = admin_command_bt.Party
    user = BasicUser.from_message(message)
    data_searchers: dict = __redis_random__.get_cached()
    data_waiting: dict = __redis_random_waiting__.get_cached()

    if text == p.users_searching:
        size = len(data_searchers.keys())
        await message.answer(
            text=f"На данный момент сейчас в поиске: {markdown.hbold({size})} юзеров."
        )

    elif text == p.users_waiting:
        size = len(data_waiting.keys())
        await message.answer(
            text=f"На данный момент сейчас юз-комнат: {markdown.hbold({size})} ."
        )

    elif text == p.users_ids_searching:
        users_text = "\n".join(data_searchers.keys())
        file_bytes = users_text.encode('utf-8')
        file = BufferedInputFile(file_bytes, filename="users.txt")

        await bot.send_document(chat_id=user.user_id, document=file, caption=f"Cписок юзеров {dateMSC}")

    elif text == reply_back_bt.back:
        await admin_panel(message, state)

    elif text == empty_bt:
        await message.answer(text="Декоративная кнопка.")

@router.message(F.text.in_(many_kds), StateFilter(Admin_menu.rmany))
async def many_panel(message: Message, state: FSMContext):
    user = BasicUser.from_message(message)
    text = message.text
    m = admin_command_bt.Many

    if text == m.add_chats:
        await message.answer(
            text=
            f'Введите чаты раздельно по пробелам:\n'
            f'Пример: 1234 2345 3456 и тд.\n',
            reply_markup=back_bt()
        )
        await state.set_state(Admin_menu.Task.add_chat)

    elif text == m.count_rooms:
        pass

    elif text == m.count_users_in_room:
        pass
    
    elif text == m.empty_rooms:
        pass

    elif text == m.users_searching:
        pass

    elif text == m.add_chats_API:
        if user.user_id != BOSS_ID:
            await message.answer(
                text=f"✋ ццц Извини ты не {markdown.hlink("босс", f"tg//user?id={BOSS_ID}")}. Тебе доступа нет.",
                reply_markup=AdminFuctional().many_from()
                )
        else:
            await message.answer(
                text=
                f"Введите {markdown.hbold('число')} чатов сколько хотите добавить:\n"
                f"❓ Макс. {markdown.hbold(maximum_chats)} чатов в день.\n",
                reply_markup=back_bt(),
            )
            await state.set_state(Admin_menu.Task.add_chat_API)

    elif text == reply_back_bt.back:
        await admin_panel(message, state)

    elif text == empty_bt:
        await message.answer(text="Декоративная кнопка.")

@router.message(StateFilter(Admin_menu.Task.add_chat_API))
async def add_chat_API(message: Message, state: FSMContext, db_session: AsyncSession):
    user = BasicUser.from_message(message)
    text = message.text
    back = await admin_back_check(text, state, message, "many")
    if back:
        return
    
    if admin_command_bt.Many.add_chats_API:
        if text.isdigit():
            itext = int(text)

            if itext < maximum_chats and itext > 0:
                success_count = 0
                for i in range(itext):
                    await asyncio.sleep(2)
                    chat_id, _ = await RandomGroupMeet(None, None).create_private_group(group_title=group_title)
                    if chat_id:
                        success_count += 1
                        logger.info(
                            f'Успешно создан приватный чат: {chat_id}\n'
                            f'По счету: {i + 1}/{itext}\n'
                        )
                        chatb = BaseDAO(PrivateChats, db_session)
                        await chatb.create(
                            data={
                                'chat_id': chat_id,
                                'data_created': dateMSC.replace(tzinfo=None),  
                            }
                        )
                        logger.info(f'Успешно добавлен в бд: {chat_id}\n')

                    else:
                        logger.warning(f'Не вернулся chat_id из функции create_private_group --{chat_id}')
                        continue
        # log block
                await message.answer(
                    text=
                    f"{f'✅ Успешно добавленны чаты: «{markdown.hbold(success_count)}/{itext}»' if itext != 0 else \
                    f'❌ Ни один чат не был добавлен. «{success_count}/{itext}»'}\n"
                    f"Продолжайте вводить, либо вренитесь в меню нажав на кнопку «{reply_back_bt.back}»",
                    reply_markup=back_bt()
                    )
            else:
                await message.answer(
                    text=
                    f" ❗️ Ваше число меньше 0 либо больше макс. значения {maximum_chats}.\n"
                    f"Пожалуйста введите число чатов от 1 до {maximum_chats}."
                    )

        else:
            await message.answer(
                text=
                " ❗️ Не числовое значение.\n"
                f"Пожалуйста введите число чатов от 1 до {maximum_chats}."
                )
        return
     

@router.message(StateFilter(Admin_menu.Task.add_chat))
async def enter_chats(message: Message, state: FSMContext, db_session: AsyncSession):
    valid_chats = []
    invalid_chats = []

    text = message.text
    back = await admin_back_check(text, state, message, "many")
    if back:
        return

    chats_ids = text.strip().split()
    total_chats = len(chats_ids)
    
    if total_chats < 1:
        await message.answer(
            text=
            ' ❗️ Ни переданно ни одного чата.\n'
            f'Пожалуйста, пришлите {markdown.hbold("id")} самого чата:\n',
            reply_markup=back_bt()
            )
        await state.set_state(Admin_menu.Task.cagain)

    for chat_id in chats_ids:
        try:
            if not chat_id.isdigit():
                logger.warning(f"Неверный формат ID чата: {chat_id}")
                invalid_chats.append(chat_id)
                continue
            
            chat_id_valid = "-100" + chat_id
            chat_id = int(chat_id)
            member = await bot.get_chat_member(chat_id_valid, bot.id)
            try:
                if member.status in ("administrator", "creator"):
                    valid_chats.append(chat_id)
                    logger.info(f"Валидный чат: {chat_id}")
                else:
                    invalid_chats.append(chat_id)
                    logger.info(f"Нет чата: {chat_id} -бота нет либо он не админ")
            
            except Exception as e:
                logger.info(f'Бот "left"/"kicked" из группы: {chat_id}')
                invalid_chats.append(chat_id)

        except Exception as e:
            logger.error(f"Ошибка при проверке чата {chat_id}: {e}")
            invalid_chats.append(chat_id)
    
    chatb = BaseDAO(PrivateChats, db_session)
    added_chats = 0
    for chids in valid_chats:
        try:
            chat_inf = await chatb.get_one(PrivateChats.chat_id == chids)
            if chat_inf:
                logger.info(f"Такой чат уже есть: {chids} -пропускаем")
                continue
            else:
                await chatb.create(data={
                    'chat_id': chids,
                    'data_created': dateMSC.replace(tzinfo=None),
                })
                added_chats += 1
                logger.info(f"Добавлен чат в бд: {chids}")
        except Exception as e:
            logger.error(f"Ошибка при добавлении чата {chids} в БД: {str(e)}")
            continue

    await message.answer(
        f'📉 Статистика обработки чатов:\n'
        f'Всего чатов: {total_chats}\n'
        f'Успешно добавлено: {added_chats}\n'
        f'Пропущено (уже есть в базе): {len(valid_chats) - added_chats}\n'
        f'Невалидных: {len(invalid_chats)}\n'
        f'{samples_log}\n'
        f'Вводите снова, либо нажмите на «{main_commands_bt.back}»'
    )

@router.message(StateFilter(Admin_menu.Task.cagain))
async def again_enter(message: Message, state: FSMContext, db_session: AsyncSession):
    curren_state = await state.get_state()
    if curren_state == Admin_menu.Task.cagain:
        await enter_chats(message, state, db_session)

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
