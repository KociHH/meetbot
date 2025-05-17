from kos_Htools.sql.sql_alchemy import BaseDAO
from data.sqlchem import User
from sqlalchemy.ext.asyncio import AsyncSession

userb = BaseDAO(User, AsyncSession)