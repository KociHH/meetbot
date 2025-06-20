from data.middleware.db_middle import engine
import asyncio
from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, String, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

base = declarative_base()
class User(base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True)
    full_name = Column(String, nullable=True)
    pseudonym = Column(String, nullable=True)
    last_activity = Column(DateTime, nullable=False)
    admin_status = Column(String, nullable=False, default='user')
    
    searcher = relationship('SearchUser', back_populates='user', uselist=False)

class PrivateChats(base):
    __tablename__ = 'chats'
    
    chat_id = Column(BigInteger, primary_key=True)
    empty = Column(Boolean, default=True, nullable=False)
    data_created = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint('chat_id', name='uq_chat_id'),
    )

class SearchUser(base):
    __tablename__ = 'searchers'
    
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    search_number = Column(BigInteger, nullable=False)
    chat_id_user = Column(BigInteger, ForeignKey('chats.chat_id', ondelete='SET NULL'))
    
    user = relationship('User', back_populates='searcher')
    chat = relationship('PrivateChats', backref='searchers')

async def create_tables():
    async with engine.begin() as create:
        await create.run_sync(base.metadata.create_all)
