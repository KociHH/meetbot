from keyboards.button_names import (
    main_commands_bt,
    admin_command_bt,
    chats_bt,
    admin_command_bt,
    reply_back_bt,
    search_again_bt,
    edit_count_users
)


command_chats = [
    chats_bt.one,
    chats_bt.two
]

main_command_list = [
    main_commands_bt.find,
    main_commands_bt.stop,
    main_commands_bt.back,
    search_again_bt.search,
    edit_count_users
]

admin_list = [
    admin_command_bt.root.party,
    admin_command_bt.root.many,
]


party_kds = [
    admin_command_bt.Party.users_searching,
    admin_command_bt.Party.users_waiting,
    admin_command_bt.Party.users_ids_searching,
]

many_kds = [
    admin_command_bt.Many.add_chats,
    admin_command_bt.Many.count_rooms,
    admin_command_bt.Many.count_users_in_room,
    admin_command_bt.Many.empty_rooms,
    admin_command_bt.Many.users_searching,
    admin_command_bt.Many.add_chats_API,
    reply_back_bt.back
]



