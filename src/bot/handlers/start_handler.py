from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from src.string_parser import string_parser
from src.mongo_manager.mongo_manager import mongo_manager
from src.crypto_impl.tron import tron_implement
import os


router = Router()


@router.message(CommandStart())
async def start_command_handler(message: Message) -> None:
    db = await mongo_manager.get_database()
    users_collection = db["user"]
    wallets_collection = db["wallets"]

    if message.from_user.id != int(os.getenv("TELEGRAM_USERID")):
        return

    user = await users_collection.find_one({"user_id": message.from_user.id})
    if not user:
        new_user = {
            "user_id": message.from_user.id,
            "username": message.from_user.username,
        }

        new_wallet = {}
        await users_collection.insert_one(new_user)

    await message.answer(text=string_parser("welcome_message"), parse_mode="HTML")
