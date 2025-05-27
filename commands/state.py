from aiogram.fsm.state import StatesGroup, State

class Main_menu(StatesGroup):
    main = State()
    
class Menu_chats(StatesGroup):
    system_chats = State()
    
class find_groups(StatesGroup):
    main = State()
    enter_users = State()
    
class Admin_menu(StatesGroup):
    main = State()
    
    search_us_panel = State()
    rooms_panel = State()
    back = State()
    

class random_user(StatesGroup):
    main = State()

    if_null = State()
    again_name = State()

    search_again = State()

class Back(StatesGroup):
    main_menu = State()
