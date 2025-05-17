import asyncio
import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from data.redis_instance import __redis_room__, __redis_users__, redis_random_waiting
from keyboards.callback_datas import Subscriber, Talking
from utils.dataclass import BasicUser
from utils.other import bot, dp, changes_to_random_waiting, delete_meet
from aiogram.utils import markdown
from keyboards.reply_button import search_again
from aiogram.fsm.context import FSMContext
from state import random_user
import re

logger = logging.getLogger(__name__)
router = Router(__name__)

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
    match = re.match(r'^communicate:(\\d+)$', call.data)
    msg_id = int(match.group(1)) if match else call.message.message_id

    room_id, result, users = changes_to_random_waiting(user.user_id, 'ready', True)
    
    if result:
        user_ids = list(users.keys())
        if all(users[uid].get('ready') for uid in user_ids):
            for users_id in user_ids:
                await bot.edit_message_text(
                    text=f"tg://user?id={users_id}",
                    chat_id=users_id,
                    message_id=msg_id
                )
                data = delete_meet(room_id)
                if data:
                    logger.info(f'Была успешно удалена комната: {room_id}')
                else:
                    logger.error(f'[Оишбка] не была удалена комната: {room_id}')

        logger.info(f'{user.user_id} принял запрос на общение')
        await call.message.edit_text(text=f'{markdown.hbold("Ваш ответ был обработан")}. Ожидаем ответ собеседника ⏸️')
    else:
        logger.warning(f'Пользователь {user.user_id} не найден ни в одной комнате')
        return False

@router.callback_query(Talking.search)
async def skip_talk(call: CallbackQuery, state: FSMContext):
    user = BasicUser.from_message(call.message)
    room_id, result = changes_to_random_waiting(user.user_id, 'ready', False)
    if result:
        data = delete_meet(room_id)
        if not data:
            logger.error(f'[Ошибка] не была удалена комната: {room_id}')

        logger.info(f'Удалена комната встречи: {room_id} для {user.user_id}')
        await call.message.edit_text(
            text='Вы проигнорировали предложение.\n Нажмите на команду /find или на кнопку ниже, чтобы возобновить поиск',
            reply_markup=search_again()
            )
        await state.set_state(random_user.search_again)

    else:
        logger.error(f'Пользователь {user.user_id} не найден ни в одной комнате\n Комната {room_id} не будет удалена.')
        return False
    
