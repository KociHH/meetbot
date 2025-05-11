from functools import wraps
import logging
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

logger =logging.getLogger(__name__)

# no work
def border(func: callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        
        if isinstance(result, str):
            sentences = result.split('\n')
            max_length = max([len(sentence) for sentence in sentences])
            border_line = '—' * (30)
            
            framed = []
            for sentence in sentences:
                if not sentence:
                    framed.append(f'| {"".ljust(max_length)} |')
                else:
                    framed.append(f'| {sentence.ljust(max_length)} |') 
            
            result = "\n".join([border_line] + framed + [border_line])
               
        return result
    return wrapper