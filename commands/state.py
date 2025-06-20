from aiogram.fsm.state import State, StatesGroup

class Main_menu(StatesGroup):
    main = State()
    
class Menu_chats(StatesGroup):
    system_chats = State()
    
class find_groups(StatesGroup):
    enter_users = State()
    again = State()
    start_searching = State()
    
class Admin_menu(StatesGroup):
    main = State()
    rparty = State()
    rmany = State()
    cagain = State()

    class Task(StatesGroup):
        add_chat = State()
        cagain = State()
        add_chat_API = State()
    

class random_user(StatesGroup):
    main = State()
    search_again = State()
    if_null = State()
    again_name = State()

class Back(StatesGroup):
    back = State()
