from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from src.string_parser import string_parser

router = Router()


@router.message(CommandStart())
async def start_command_handler(message: Message) -> None:
    await message.answer(text=string_parser("welcome_message"), parse_mode="HTML")
