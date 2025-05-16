from dataclasses import dataclass
from functools import wraps
import logging
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

logger =logging.getLogger(__name__)

@dataclass(eq=False)
class BasicUser:
    user_id: int
    username: str | None
    full_name: str | None

    first_name: str | None
    last_name: str | None

    @classmethod
    def from_message(cls, message: Message) -> 'BasicUser':
        user = message.from_user
        return cls(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            
            first_name=user.first_name,
            last_name=user.last_name
        )
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "user_name": self.username,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name
        }
        
