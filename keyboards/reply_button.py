from venv import logger
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from .button_names import main_commands_bt, chats_bt, admin_command_bt, search_again_bt, reply_back_bt, empty_bt


def chats() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=chats_bt.one)
    builder.button(text=chats_bt.two)
    builder.adjust(1, 1)
    return builder.as_markup(resize_keyboard=True)

def main_commands(buttons: list[str] | None = None) -> ReplyKeyboardMarkup:
    try:
        builder = ReplyKeyboardBuilder()
        builder.button(text=main_commands_bt.find)
        builder.button(text=main_commands_bt.stop)
        builder.button(text=main_commands_bt.back)
        if buttons:
            size = len(buttons)
            for nm in buttons:
                builder.button(text=nm)
            builder.adjust(2, size + 1)
        else:
            builder.adjust(2, 1)
    except Exception as e:
        logger.error(f'в main_commands:\n {e}')
    return builder.as_markup(resize_keyboard=True)

def back_bt() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=main_commands_bt.back)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

class AdminFuctional:
    def __init__(self):
        pass
    
    def empty(self, builder: ReplyKeyboardBuilder) -> None:
        builder.button(text=empty_bt)
    
    def back(self, builder: ReplyKeyboardBuilder) -> None:
        builder.button(text=reply_back_bt.back)
    
    def root(self) -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.button(text=admin_command_bt.root.party)
        builder.button(text=admin_command_bt.root.many)
        builder.adjust(2)
        return builder.as_markup(resize_keyboard=True)

    def party_from(self) -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.button(text=admin_command_bt.Party.users_searching)
        builder.button(text=admin_command_bt.Party.users_waiting)
        builder.button(text=admin_command_bt.Party.users_ids_searching)
        self.back(builder)
        builder.adjust(3, 1)
        return builder.as_markup(resize_keyboard=True)

    def many_from(self) -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.button(text=admin_command_bt.Many.add_chats)
        builder.button(text=admin_command_bt.Many.count_rooms)
        builder.button(text=admin_command_bt.Many.count_users_in_room)
        builder.button(text=admin_command_bt.Many.empty_rooms)
        builder.button(text=admin_command_bt.Many.users_searching)
        builder.button(text=admin_command_bt.Many.add_chats_API)
        self.back(builder)
        builder.adjust(3, 3, 1)
        return builder.as_markup(resize_keyboard=True)
