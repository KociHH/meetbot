empty_bt = 'ᅟ'
edit_count_users = 'Изменить значение юзеров для поиска.'

class chats_bt:
    one = '1 🗣'
    two = '2 👥'

class main_commands_bt:
    find = "🔍 Искать"
    stop = "🚫 Стоп" 
    back = "🔙"

class admin_command_bt:
    class root:
        party = f'Инф. {chats_bt.one}'
        many =  f'Инф. {chats_bt.two}'
    
    class Many:
        users_searching = 'Кол-во юзеров в поиске'
        count_rooms = 'Кол-во комнат'
        empty_rooms = 'Кол-во пустующих комнат'
        count_users_in_room = 'Вывод каждой комнаты с юзерами в ней'
        add_chats = 'Добавить чат(-ы)'
        add_chats_API = '🚨 «API» Добавить чаты'

    class Party:
        users_searching = 'Кол-во юзеров в поиске'
        users_ids_searching = "Файл user_id юзеров в поиске"
        users_waiting = 'Кол-во юз-комнат ожидающие ответа'


class search_again_bt:
    search = 'Искать снова 🔄'
    
class reply_back_bt:
    back = '🔙'
