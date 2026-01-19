from aiogram import Bot, Dispatcher
from src.mongo_manager.mongo_manager import mongo_manager
import asyncio
import os
import logging
from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_name == "emit":
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


logging.basicConfig(handlers=[InterceptHandler()], level=0)
logger.add("logs/bot.log", rotation="500 MB", retention="10 days", level="INFO")

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()


async def main():
    logger.info("Starting bot...")
    db = await mongo_manager.connect()

    try:
        await dp.start_polling(bot)
    finally:
        await mongo_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
