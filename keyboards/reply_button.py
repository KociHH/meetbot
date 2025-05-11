from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from .button_names import name_state_bt, yes_no_bt, main_commands_bt, admin_command_bt, man_woman_bt, menu_chating_bt

def name_state() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=name_state_bt.leave)
    builder.button(text=name_state_bt.mine)
    builder.button(text=name_state_bt.skip)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def yes_no() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=yes_no_bt.yes)
    builder.button(text=yes_no_bt.change_gender)
    builder.button(text=yes_no_bt.change_nickname)
    builder.adjust(1, 2)
    return builder.as_markup(resize_keyboard=True)

def menu_chating() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=menu_chating_bt.systems_chats)
    return builder.as_markup(resize_keyboard=True)

def chats() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text='1')
    builder.button(text='2')
    builder.adjust(1)
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
    return builder.as_markup(resize_keyboard=True)

def man_woman() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(man_woman_bt.woman)
    builder.button(man_woman_bt.man)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)