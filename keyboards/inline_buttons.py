from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .callback_datas import Talking, ContinueSearch
from keyboards.callback_datas import Subscriber

def go_tolk() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ общаться', callback_data=Talking.communicate)
    builder.button(text='🔇', callback_data=Talking.search)
    builder.adjust(2)
    return builder.as_markup()

def continue_search_button(call_data: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='Продолжить поиск 🔄', callback_data=call_data)
    return builder.as_markup()

def sub_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Канал", url='https://t.me/kosiniii')
    builder.button(text='Проверка подписки 🚀', callback_data=Subscriber.check_button)
    builder.adjust(1, 1)
    return builder.as_markup()