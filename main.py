import asyncio
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update
import logging
from aiogram import Bot, Dispatcher, Router, F
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
import uvicorn
from config import BOT_TOKEN, WEB_HOOK_URL, WEB_HOOK_HOST, WEB_HOOK_PORT, CHANNEL_ID
from aiogram.enums import ParseMode
from commands import router as main_router
from data.middleware.db_middle import WareBase, listclonWare, session_engine, checkerChannelWare
from data.sqlchem import create_tables
from data.redis_instance import users
from kos_Htools.telethon_core.clients import multi
from commands.message_bot import result
from aiogram.types import Message
from utils.other import bot, dp

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# bot
webhook = WEB_HOOK_URL
if '/webhook' not in WEB_HOOK_URL:
    webhook = WEB_HOOK_URL + '/webhook'
  
@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != webhook:
        dp.include_router(main_router)
        await bot.set_webhook(webhook)
        asyncio.run(create_tables())
        logger.info(
            f'Бот запускается...\n'
            f'INFO: {webhook_info}'
            )
    yield
    logger.info('Бот зыкрывается...')
    await bot.delete_webhook()
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

@app.post('/webhook')
async def bot_setwebhook(request: Request):
    try:
        dp.message.middleware(listclonWare(users.redis_data().get('users', []), target_handler='reply_command'))
        dp.message.middleware(checkerChannelWare(CHANNEL_ID))
        dp.update.middleware(WareBase(session_engine))
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return {'status': 'ok'}
    
    except Exception as e:    
        logger.error(f'webhook ошибка: {e}')
        return {'status': 'error'}

    
if __name__ == "__main__":
    uvicorn.run(app, host=WEB_HOOK_HOST, port=int(WEB_HOOK_PORT))