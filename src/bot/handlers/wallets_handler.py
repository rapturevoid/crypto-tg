from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from src.string_parser.string_parser import parser as string_parser, inline

router = Router()


@router.callback_query(lambda c: c.data == "wallets")
async def wallets_handler(callback: CallbackQuery) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=inline.get("tron_wallets"), callback_data="tron_wallets"
                )
            ],
            # [
            #     InlineKeyboardButton(
            #         text=inline.get("bitcoin_wallets"), callback_data="bitcoin_wallets"
            #     )
            # ],
        ]
    )
    await callback.message.answer(
        text=string_parser.get("available_networks"),
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()
