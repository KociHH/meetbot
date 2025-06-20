import asyncio
from aiogram.types import Update
import logging
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
import uvicorn
from config import BOT_TOKEN, WEB_HOOK_URL, WEB_HOOK_HOST, WEB_HOOK_PORT, CHANNEL_ID
from commands import router as main_router
from data.middleware.db_middle import WareBase, session_engine, checkerChannelWare
from data.sqlchem import create_tables
from utils.other import bot, dp
from data.redis_instance import cheking_keys
from utils.other import ErrorPrefixFilter
from kos_Htools.telethon_core import multi

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(ErrorPrefixFilter())

setup_logging()
logger = logging.getLogger(__name__)

webhook = WEB_HOOK_URL
if '/webhook' not in WEB_HOOK_URL:
    webhook = WEB_HOOK_URL + '/webhook'

print(webhook)

@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != webhook:
        dp.include_router(main_router)
        await bot.set_webhook(webhook)
        await create_tables()
        cheking_keys()

        dp.update.middleware(WareBase(session_engine))
        dp.message.middleware(checkerChannelWare(CHANNEL_ID))
        
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
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return {'status': 'ok'}
    
    except Exception as e:    
        logger.error(f'webhook ошибка: {e}')
        return {'status': 'error'}

async def def_start(token: str | None = None):
    try:
        if token == 'bot':
            await bot.delete_webhook()
            await dp.start_polling(bot)
        else:
            config = uvicorn.Config(app, host=WEB_HOOK_HOST, port=int(WEB_HOOK_PORT))
            server = uvicorn.Server(config)
            await server.serve()

    except KeyboardInterrupt as e:
        logger.info("off")

if __name__ == "__main__":
    asyncio.run(def_start())