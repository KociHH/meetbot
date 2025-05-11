from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from keyboards.button_names import yes_no_bt, main_commands_bt, admin_command_bt, man_woman_bt


command_chats = [
    '1'
    '2'
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

man_woman_list = [
    man_woman_bt.man,
    man_woman_bt.woman
]

save_or_change = [
    yes_no_bt.yes,
    yes_no_bt.change_gender,
    yes_no_bt.change_nickname,
]