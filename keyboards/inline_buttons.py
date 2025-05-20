from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callback_datas import Talking, ContinueSearch

builder = InlineKeyboardBuilder()

def go_tolk(msg_id: int = None) -> InlineKeyboardMarkup:
    builder.button(text='✅ общаться', callback_data=Talking.with_msgid(msg_id))
    builder.button(text='😒 скип', callback_data=Talking.communicate)
    builder.adjust(2)
    return builder.as_markup()

def continue_search_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='Продолжить поиск 🔄', callback_data=ContinueSearch.continue_search)
    return builder.as_markup()

