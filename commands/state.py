from aiogram.fsm.state import StatesGroup, State

class start_register(StatesGroup):
    name = State()
    check_name = State()
    enter = State()
    gender = State()
    name = State()
    m = State()
    
class Main_menu(StatesGroup):
    main = State()

class okno(StatesGroup):
    okey = State()
    no = State()
    
class Menu_chats(StatesGroup):
    limit_alert = State()
    system_chats = State()
    
class create_room_into_tg(StatesGroup):
    main = State()
    
class Admin_menu(StatesGroup):
    main = State()