from data.middleware.db_middle import engine
import asyncio
from sqlalchemy import BigInteger, Column, String, Integer
from sqlalchemy.orm import declarative_base

base = declarative_base()
class User(base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True)
    full_name = Column(String, nullable=True)
    admin_status = Column(String, nullable=False, default='user')
    

async def create_tables():
    async with engine.begin() as create:
        await create.run_sync(base.metadata.create_all)
