from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from src.string_parser.string_parser import parser as string_parser, inline
from src.mongo_manager.mongo_manager import mongo_manager

router = Router()

keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=inline.get("wallets"), callback_data="wallets")]
    ]
)


@router.message(CommandStart())
async def start_command_handler(message: Message) -> None:
    db = await mongo_manager.get_database()
    usdt_wallet = db["usdt_wallets"]
    user_about = db["user_about"]

    total_users = await user_about.count_documents({})

    if total_users == 0:
        await user_about.insert_one(
            {
                "user_id": message.from_user.id,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
            }
        )
        await message.answer(
            text=string_parser.get("welcome_message"),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    elif await user_about.count_documents({"user_id": message.from_user.id}) > 0:
        await message.answer(
            text=string_parser.get("welcome_message"),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        await message.answer(
            text=string_parser.get("bot_already_in_use"),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
