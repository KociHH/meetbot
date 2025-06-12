import asyncio
import logging
from turtle import st
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from keyboards.inline_buttons import continue_search_button
from data.redis_instance import __redis_room__, __redis_users__, __redis_random__, redis_random, __redis_random_waiting__, redis_random_waiting
from keyboards.callback_datas import Subscriber, Talking, ContinueSearch
from utils.dataclass import BasicUser
from utils.other import bot, dp, error_logger, _send_message_to_user
from utils.celery_tools import RandomMeet, details_fromDB
from aiogram.utils import markdown
from keyboards.reply_button import main_commands
from aiogram.fsm.context import FSMContext
from .state import random_user
from aiogram.filters import or_f
from utils.time import dateMSC, time_for_redis
from keyboards.callback_datas import ContinueSearch
from data.celery.tasks import add_user_to_search, monitor_search_users_party
from config import CHANNEL_ID
from aiogram.types import CallbackQuery, Message, ChatMemberLeft
import aiogram.exceptions
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = Router(name=__name__)
wait_text = f'✔️ Ваш ответ был обработан успешно.\n⏸️ Ожидаем ответ собеседника.\n\nНажмите на кнопку ниже чтобы продолжить поиск.\n'
cancel_text = "🙅‍♂️ Эта встреча была отменена вашим собеседником. Нажмите на кнопку ниже для поиска."

@router.callback_query(F.data == Subscriber.check_button)
async def button_checker_subscriber(callback: CallbackQuery, state: FSMContext):
    user = BasicUser.from_message(message=None, call_user=callback.from_user)
    try:
        user_status = await callback.from_user.bot.get_chat_member(CHANNEL_ID, user.user_id)
        if isinstance(user_status, ChatMemberLeft):
            await callback.answer("❌ Вы не подписаны на канал!", show_alert=True)
        else:
            await callback.answer('✅')
            await callback.message.delete()
            from commands.basic_command import menu_chats
            await menu_chats(message=callback.message, state=state)
            
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки: {e}")
        await callback.answer("Произошла ошибка при проверке подписки", show_alert=True)


@router.callback_query(F.data == Talking.communicate)
async def sucsess_talk(call: CallbackQuery, db_session: AsyncSession):
    user = BasicUser.from_message(message=None, call_user=call.from_user)
    rm = RandomMeet(user.user_id)
    data =  __redis_random__.get_cached()
    _, users, _ = rm.getitem_to_random_waiting(return_full_info=True)
    error_users = []
    if users:
        error_users = [us for us in users.keys() if us not in data]
    else:
        logger.info(f'users: {type(users)}, не нашел {user.user_id} в random_waiting')

    if error_users:
        logger.error(f'Юзер-ы по неизвестной причине не добавленны в random_waiting либо были удалены:\n{error_users}')
        await call.answer("☝️")
        try:
            await call.message.edit_text(
                text=f"🕗 Прошло долгое время. Вы не можете начать общение.",
            )
        except Exception as e:
            logger.error(error_logger(False, 'sucsess_talk', e))
        return

    rm = RandomMeet(user.user_id)
    room_id, result, users = rm.getitem_to_random_waiting(field='ready', value=True, complete_update=True)
    print(room_id, result, users)

    if result:
        message_count = int(rm.getitem_to_random_user(item='message_count'))
        reset = rm.reset_rdata(items=['added_time', 'last_animation_text', 'continue_id'], add={'message_count': message_count - 1})
        if not reset:
            logger.error(f'Данные {user.user_id} не обнулились')

        user_ids = users.keys()
        user_ids_list = list(user_ids)
        
        if len(user_ids_list) == 2 and all(users.get(uid).get('ready') for uid in user_ids_list):
            user1_id_str = user_ids_list[0]
            user2_id_str = user_ids_list[1]
            users_int = [int(user1_id_str), int(user2_id_str)]
            full_data_users: dict = await details_fromDB(
                db_session=db_session,
                users=users_int,
                name_or_pseudonym=True,
                )

            if full_data_users:
                user_names = {}
                for uid in users_int:
                    user_info: dict = full_data_users.get(uid)
                    if user_info:
                        user_names[uid] = user_info.get('name_or_pseudonym') or user_info.get('user_inf').full_name

                for current_user_id_int in users_int:
                    partner_user_id_int = next(uid for uid in users_int if uid != current_user_id_int)
                    partner_user_name = user_names.get(partner_user_id_int, 'Здесь')

                    rm_current = RandomMeet(current_user_id_int)
                    edit_message_id = rm_current.getitem_to_random_waiting('message_id', return_value=True)

                    message_text_to_send = f"🔔 Твой партнер -> {markdown.hlink(f'{partner_user_name}', f'tg://user?id={partner_user_id_int}')}"
                    logger.info(f"Для пользователя {current_user_id_int}: Partner ID: {partner_user_id_int}, Ссылка: {message_text_to_send}")

                    try:
                        await bot.edit_message_text(
                            text=message_text_to_send,
                            chat_id=current_user_id_int,
                            message_id=edit_message_id,
                            reply_markup=continue_search_button(ContinueSearch.continue_search_edit),
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось отредактировать сообщение для {current_user_id_int} (message_id: {edit_message_id}): {e}. Отправленно новое сообщение.")
                        await bot.send_message(
                            chat_id=current_user_id_int,
                            text=message_text_to_send,
                            reply_markup=continue_search_button(ContinueSearch.continue_search_edit),
                        )

            if rm.delete_meet(room_id):
                logger.info(f'Была успешно удалена комната: {room_id}')
                return
            else:
                logger.error(f'[Оишбка] не была удалена комната: {room_id}')

        logger.info(f'{user.user_id} принял запрос на общение')
        try:
            await call.message.edit_text(text=wait_text, reply_markup=continue_search_button(ContinueSearch.continue_search_edit))
        except aiogram.exceptions.TelegramBadRequest as e:
            logger.warning(f"Не удалось отредактировать сообщение для {user.user_id} (message_id: {call.message.message_id}): {e}. Отправляю новое сообщение.")
            await call.message.answer(text=wait_text, reply_markup=continue_search_button(ContinueSearch.continue_search_edit))
    else:
        logger.warning(f'Пользователь {user.user_id} не найден ни в одной комнате в changes_to_random_waiting')
        return

@router.callback_query(F.data == Talking.search)
async def skip_talk(call: CallbackQuery):
    user = BasicUser.from_message(message=None, call_user=call.from_user)
    rm = RandomMeet(user.user_id)
    _, users, _ = rm.getitem_to_random_waiting(return_full_info=True)
    error_users = [us for us in users.keys() if us not in __redis_random__.get_cached()]
    
    if error_users:
        logger.error(f'Юзер-ы по неизвестной причине не добавленны в random_waiting либо были удалены:\n{error_users}')
        await call.answer("☝️")
        try:
            await call.message.edit_text(text="🕗 Прошло долгое время. Вы не можете пропустить собеседника.",)
        except Exception as e:
             logger.error(f"Не удалось отредактировать сообщение после остановки поиска (skip_talk): {e}")
        return
    else:
        room_id, result, users = rm.getitem_to_random_waiting(field='ready', value=False, complete_update=True)
        if result:
            partner_id = next(int(us) for us in users.keys() if int(us) != user.user_id)
            partner_msd = RandomMeet(partner_id).getitem_to_random_waiting(field='message_id', return_value=True,)
            message_count = int(rm.getitem_to_random_user(item='message_count'))
            reset = rm.reset_rdata(items=['added_time', 'last_animation_text', 'continue_id'], add={'message_count': message_count - 1})
            if not reset:
                logger.error(f'Данные {user.user_id} не обнулились')
 
            data_after_delete = rm.delete_meet(room_id)
            if data_after_delete is not False:
                logger.info(f'Удалена комната встречи: {room_id} для {users}')
            else:
                logger.error(f'[Ошибка] не была удалена комната: {room_id}')

            try:
                await bot.edit_message_text(
                    text=cancel_text,
                    chat_id=partner_id,
                    message_id=partner_msd,
                    reply_markup=continue_search_button(ContinueSearch.continue_search)
                )
            except Exception as e:
                logger.error(f'Не получилось отредактировать сообщение {partner_id} идет отправка сообщения:\n {e}')
                await bot.send_message(
                    chat_id=partner_id,
                    text=cancel_text,
                    reply_markup=continue_search_button(ContinueSearch.continue_search),
                )

            await call.message.edit_text(
                text=f'🙈 Вы проигнорировали предложение.\nНажмите на кнопку ниже, чтобы возобновить поиск.',
                reply_markup=continue_search_button(ContinueSearch.continue_search)
                )

        else:
            logger.error(f'Пользователь {user.user_id} не найден ни в одной комнате в changes_to_random_waiting\n Комната {room_id} не будет удалена.')
            return


@router.callback_query(or_f(F.data == ContinueSearch.continue_search, F.data == ContinueSearch.continue_search_edit))
async def handle_continue_search(call: CallbackQuery):
    user_id = call.from_user.id
    message = call.message
    rm = RandomMeet(user_id)

    if message:
        try:
            logger.info(f'Пользователь {user_id} продолжил поиск по кнопке')
            await call.answer(text='🔍')

            if not call.data == ContinueSearch.continue_search_edit:
                await message.delete()    
            message_obj = await message.answer(text='Идет поиск')

            rm.reset_rdata(items=['continue_id', 'added_time'])
            add_user_to_search.delay(message_obj.message_id, user_id, redis_random)
            monitor_search_users_party.delay()

        except Exception as e:
            logger.error(f'[Ошибка] при обработке callback_query продолжения поиска для {user_id}: {e}')
            await call.answer(text='🚫 Произошла ошибка.')
    else:
        logger.error(f'[Ошибка] message отсутствует в callback_query для пользователя {user_id}')
        await call.answer(text='🚫 Произошла ошибка.')