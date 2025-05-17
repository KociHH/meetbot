from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callback_datas import Talking

builder = InlineKeyboardBuilder()

def go_tolk(msg_id: int = None) -> InlineKeyboardMarkup:
    builder.button(text='✅ общаться', callback_data=Talking.with_msgid(msg_id))
    builder.button(text='😒 скип', callback_data=Talking.communicate)
    builder.adjust(2)
    return builder.as_markup()

