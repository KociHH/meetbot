from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from keyboards.button_names import main_commands_bt, admin_command_bt, chats_bt, admin_command_bt, reply_back_bt


command_chats = [
    chats_bt.one,
    chats_bt.two
]

main_command_list = [
    main_commands_bt.find,
    main_commands_bt.stop,
    main_commands_bt.back
]

admin_list = [
    admin_command_bt.users_active,
    admin_command_bt.rooms,
]

admin_panels_info = [
    admin_command_bt.rooms_all_info,
    admin_command_bt.users_searching,
    reply_back_bt.back
]



