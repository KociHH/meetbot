from dataclasses import dataclass
from functools import wraps
import logging
from aiogram.types import Message, User
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

@dataclass(eq=False)
class BasicUser:
    user_id: int
    username: str | None
    full_name: str | None

    first_name: str | None
    last_name: str | None

    @classmethod
    def from_message(cls, message: Message | None, call_user: User | None = None) -> 'BasicUser':
        user_obj = None
        if call_user:
            user_obj = call_user
        elif message:
            user_obj = message.from_user
        
        if not user_obj:
            raise ValueError("No user information provided.")
        
        return cls(
            user_id=user_obj.id,
            username=user_obj.username,
            full_name=user_obj.full_name,
            
            first_name=user_obj.first_name,
            last_name=user_obj.last_name
        )
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "user_name": self.username,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name
        }
        
