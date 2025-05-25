from sqlalchemy.ext.asyncio import async_sessionmaker

from data.sqlchem import User # Импортируйте ваши модели здесь
# from kos_Htools.sql.sql_alchemy.dao import BaseDAO # Убираем импорт BaseDAO, так как он не будет использоваться глобально

# async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
# session_engine = async_session_factory # Предполагая, что session_engine - это ваша фабрика сессий

# Инициализация DAO (убираем глобальную инициализацию userb)
# userb = BaseDAO(User, session_engine)

# Другие глобальные DAO или объекты, если есть

# В дальнейшем, экземпляры BaseDAO будут создаваться локально в асинхронных функциях при необходимости,
# используя сессию, полученную из session_engine.