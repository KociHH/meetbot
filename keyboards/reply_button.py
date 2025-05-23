from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from .button_names import main_commands_bt, chats_bt, admin_command_bt, search_again_bt


def chats() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=chats_bt.one)
    builder.button(text=chats_bt.two)
    builder.adjust(1, 1)
    return builder.as_markup(resize_keyboard=True)

def main_commands() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=main_commands_bt.find)
    builder.button(text=main_commands_bt.stop)
    builder.button(text=main_commands_bt.back)
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def admin_command() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=admin_command_bt.users_active)
    builder.button(text=admin_command_bt.rooms)
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def search_again() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=search_again_bt.search)
    builder.adjust(1)
    return builder.as_markup()

def back_bt() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=main_commands_bt.back)
    builder.adjust(1)
    return builder.as_markup()