class Talking:
    @staticmethod
    def with_msgid(msg_id: int | None = None):
        if msg_id:
            return f'communicate:{msg_id}'
        return 'communicate'

    communicate = 'communicate'
    search = 'search'

class Subscriber:
    check_button = 'check_button'