import asyncio
import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from data.utils import CreatingJson
from data.redis_instance import __redis_room__, __redis_users__, random_users
from keyboards.callback_datas import Subscriber, Talking, ContinueSearch
from utils.dataclass import BasicUser
from utils.other import bot, dp, error_logger
from utils.other_celery import RandomMeet
from aiogram.utils import markdown
from keyboards.reply_button import search_again
from aiogram.fsm.context import FSMContext
from .state import random_user
import re
from utils.time import dateMSC
from keyboards.callback_datas import ContinueSearch

logger = logging.getLogger(__name__)
router = Router(name=__name__)

@router.callback_query(F.data == Subscriber.check_button)
async def button_checker_subscriber(callback: CallbackQuery, data: dict):
    try:
        if data.get('is_subscribed', False):
            await callback.answer("✅ Вы подписаны!", show_alert=True)
            await callback.message.delete(
                callback.message.chat.id,
                callback.message.message_id,
            )
            
            if 'saved_command' in data:
                saved_command = data['saved_command']
                new_message = Message(
                    message_id=callback.message.message_id + 1,
                    date=callback.message.date,
                    chat=callback.message.chat,
                    from_user=callback.message.from_user,
                    text=saved_command
                )
                await dp.message.middleware.trigger(new_message, data)
                data.pop('saved_command', None)
        else:
            await callback.answer("❌ Вы не подписаны на канал!", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки: {e}")
        await callback.answer("Произошла ошибка при проверке подписки", show_alert=True)


@router.callback_query(F.data.regexp(r'^communicate:(\\d+)$'))
async def sucsess_talk(call: CallbackQuery):
    user = BasicUser.from_message(call.message)
    user_id_str = str(user.user_id)
    if user_id_str not in random_users.redis_data():
        await call.answer("Ваш поиск уже остановлен.", show_alert=True)
        try:
            await call.message.edit_text(
                text=f"Ваш поиск был {markdown.hcode('остановлен')}. Вы не можете узнать информацию о собеседнике.\n Пока он не подтвердит общение.",
            )
        except Exception as e:
            logger.error(error_logger(False, 'sucsess_talk', e))

    rn = RandomMeet(user.user_id)
    room_id, result, users = rn.changes_to_random_waiting('ready', True)
    
    if result:
        partner_id = next(us for us in users.keys() if us != user.user_id)
        data = random_users.redis_data()
        user_data = data.get(user_id_str, {})
        tolk_users = user_data.get('tolk_users', [])
        if partner_id not in tolk_users:
            tolk_users.append(partner_id)

        user_data['tolk_users'] = tolk_users
        user_data['data_activity'] = dateMSC
        data[user_id_str] = user_data
        random_users.redis_cashed(data=data)
        user_ids = list(users.keys())
        if all(users[uid].get('ready') for uid in user_ids):
            for users_id in user_ids:
                await bot.edit_message_text(
                    text=f"Твой партнер {markdown.hlink('тут', f'tg://user?id={users_id}')}",
                    chat_id=users_id,
                    message_id=call.message.message_id
                )
                data = rn.delete_meet(room_id)
                if data:
                    logger.info(f'Была успешно удалена комната: {room_id}')
                else:
                    logger.error(f'[Оишбка] не была удалена комната: {room_id}')
        logger.info(f'{user.user_id} принял запрос на общение')
        await call.message.edit_text(text=f'{markdown.hbold("Ваш ответ был обработан")}. Ожидаем ответ собеседника ⏸️')
    else:
        logger.warning(f'Пользователь {user.user_id} не найден ни в одной комнате')
        return False

@router.callback_query(F.data == Talking.search)
async def skip_talk(call: CallbackQuery, state: FSMContext):
    user = BasicUser.from_message(call.message)
    user_id_str = str(user.user_id)

    if user_id_str not in random_users.redis_data():
        await call.answer("Ваш поиск уже остановлен.", show_alert=True)
        try:
            await call.message.edit_text(
                text="Ваш поиск был остановлен. Вы не можете пропустить собеседника.",
                reply_markup=None
            )
        except Exception as e:
             logger.error(f"Не удалось отредактировать сообщение после остановки поиска (skip_talk): {e}")
        return 

    rn = RandomMeet(user.user_id)
    room_id, result, users = rn.changes_to_random_waiting('ready', False)
    if result:
        partner_id = next(us for us in users.keys() if us != user.user_id)
        data = random_users.redis_data()
        user_data = data.get(user_id_str, {})
        skip_users = user_data.get('skip_users', [])
        if partner_id not in skip_users:
            skip_users.append(partner_id)
            
        user_data['skip_users'] = skip_users
        user_data['data_activity'] = dateMSC
        data[user_id_str] = user_data
        random_users.redis_cashed(data=data)
        data = rn.delete_meet(room_id)
        if not data:
            logger.error(f'[Ошибка] не была удалена комната: {room_id}')

        logger.info(f'Удалена комната встречи: {room_id} для {user.user_id}')
        await call.message.edit_text(
            text='🙈 Вы проигнорировали предложение.\n Нажмите на кнопку ниже, чтобы возобновить поиск 🔎',
            reply_markup=search_again()
            )
        await state.set_state(random_user.search_again)

    else:
        logger.error(f'Пользователь {user.user_id} не найден ни в одной комнате\n Комната {room_id} не будет удалена.')
        return False


@router.callback_query(F.data == ContinueSearch.continue_search)
async def handle_continue_search(call: CallbackQuery):
    user_id = call.from_user.id
    message = call.message
    
    if message:
        try:
            CreatingJson().random_data_user([user_id], {
                'continue_id': None, 
            })
            logger.info(f'Пользователь {user_id} продолжил поиск по кнопке')
            await message.delete()
            await call.answer(text='✅')

        except Exception as e:
            logger.error(f'[Ошибка] при обработке callback_query продолжения поиска для {user_id}: {e}')
            await call.answer(text='Произошла ошибка.')
    else:
        logger.error(f'[Ошибка] message отсутствует в callback_query для пользователя {user_id}')
        await call.answer(text='Произошла ошибка.')
