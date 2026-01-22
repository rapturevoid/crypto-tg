from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)
from src.string_parser.string_parser import inline, parser
from src.mongo_manager.mongo_manager import mongo_manager
from src.crypto_impl.bitcoin import bitcoin_implement
from bson import ObjectId
import secrets
import string
import time

router = Router()

transfer_states = {}


@router.callback_query(lambda c: c.data == "bitcoin_wallets")
async def bitcoin_wallets_handler(callback: CallbackQuery) -> None:
    db = await mongo_manager.get_database()
    wallets_collection = db["usdt_wallets"]

    user_wallets = await wallets_collection.find(
        {"user_id": callback.from_user.id, "network": "bitcoin"}
    ).to_list(length=None)

    if not user_wallets:
        text = parser.get("no_bitcoin_wallets")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=inline.get("add_wallet"),
                        callback_data="add_bitcoin_wallet",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=inline.get("back_to_networks"), callback_data="wallets"
                    )
                ],
            ]
        )
    else:
        text = parser.get("select_wallet")
        wallet_buttons = []
        for wallet in user_wallets:
            address = wallet.get("address", "Unknown")
            wallet_id = str(wallet.get("_id"))
            short_address = (
                address[:6] + "..." + address[-4:] if len(address) > 10 else address
            )
            wallet_buttons.append(
                InlineKeyboardButton(
                    text=short_address, callback_data=f"wallet_info:{wallet_id}"
                )
            )

        keyboard_rows = []
        for i in range(0, len(wallet_buttons), 2):
            row = wallet_buttons[i : i + 2]
            keyboard_rows.append(row)

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=inline.get("add_wallet"), callback_data="add_bitcoin_wallet"
                )
            ]
        )
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=inline.get("back_to_networks"), callback_data="wallets"
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    await callback.message.answer(text=text, reply_markup=keyboard)
    await callback.answer()


@router.message(F.text & ~F.text.startswith("/"))
async def handle_transfer_input(message: Message) -> None:
    user_id = message.from_user.id

    if user_id not in transfer_states:
        return

    state = transfer_states[user_id]

    if state["step"] == "address":
        address = message.text.strip()
        if not (
            address.startswith("1")
            or address.startswith("3")
            or address.startswith("bc1")
        ):
            await message.answer(
                text=parser.get("invalid_bitcoin_address_format"),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Отмена", callback_data="cancel_transfer"
                            )
                        ]
                    ]
                ),
            )
            return

        state["recipient_address"] = address
        state["step"] = "amount"

        await message.answer(
            text=parser.get("enter_transfer_amount", currency="BTC"),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Отмена", callback_data="cancel_transfer"
                        )
                    ]
                ]
            ),
        )

    elif state["step"] == "amount":
        try:
            amount = float(message.text.strip())
            if amount <= 0:
                raise ValueError("Amount must be positive")

            await execute_transfer(message, state, amount)

        except ValueError:
            await message.answer(
                text=parser.get("invalid_amount_format"),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Отмена", callback_data="cancel_transfer"
                            )
                        ]
                    ]
                ),
            )


@router.callback_query(lambda c: c.data == "cancel_transfer")
async def cancel_transfer_handler(callback: CallbackQuery) -> None:
    if callback.from_user.id in transfer_states:
        del transfer_states[callback.from_user.id]

    await callback.message.answer(text=parser.get("transfer_cancelled"))
    await callback.answer()


async def execute_transfer(message: Message, state: dict, amount: float) -> None:
    user_id = message.from_user.id
    wallet_id = state["wallet_id"]
    recipient_address = state["recipient_address"]

    try:
        db = await mongo_manager.get_database()
        wallets_collection = db["usdt_wallets"]

        wallet = await wallets_collection.find_one(
            {"_id": ObjectId(wallet_id), "user_id": user_id, "network": "bitcoin"}
        )

        if not wallet:
            await message.answer(text=parser.get("wallet_not_found"))
            return

        wallet_name = wallet["name"]

        tx_result = bitcoin_implement.transfer(
            wallet_name=wallet_name,
            to_address=recipient_address,
            amount=amount,
        )

        txid = tx_result["txid"]
        scan_url = tx_result["link"]

        await message.answer(
            text=parser.get("transfer_success") + f"\n\n"
            f"Получатель: <code>{recipient_address}</code>\n"
            f"Сумма: {amount} BTC\n"
            f"Хеш транзакции: <code>{txid}</code>\n\n"
            f"Посмотреть на Mempool: {scan_url}",
            parse_mode="HTML",
        )

    except Exception as e:
        error_msg = str(e)
        await message.answer(text=parser.get("transfer_error", error=error_msg))

    finally:
        if user_id in transfer_states:
            del transfer_states[user_id]


@router.callback_query(lambda c: c.data.startswith("transfer:"))
async def transfer_handler(callback: CallbackQuery) -> None:
    wallet_id = callback.data.split(":")[1]

    transfer_states[callback.from_user.id] = {"step": "address", "wallet_id": wallet_id}

    await callback.message.answer(
        text=parser.get("enter_recipient_address"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Отмена", callback_data="cancel_transfer")]
            ]
        ),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("top_up:"))
async def top_up_handler(callback: CallbackQuery) -> None:
    wallet_id = callback.data.split(":")[1]
    await callback.message.answer(text="Функция пополнения в разработке...")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("private_info:"))
async def private_info_handler(callback: CallbackQuery) -> None:
    wallet_id = callback.data.split(":")[1]

    db = await mongo_manager.get_database()
    wallets_collection = db["usdt_wallets"]

    try:
        wallet = await wallets_collection.find_one(
            {
                "_id": ObjectId(wallet_id),
                "user_id": callback.from_user.id,
                "network": "bitcoin",
            }
        )

        if not wallet:
            await callback.message.answer(text=parser.get("wallet_not_found"))
            await callback.answer()
            return

        private_key = wallet.get("private_key", "Unknown")
        mnemonic = wallet.get("mnemonic", "Unknown")

        text = (
            parser.get("private_information")
            + "\n\n"
            + parser.get("security_warning")
            + "\n\n"
            + f"Приватный ключ (WIF): <code>{private_key}</code>\n\n"
            + f"Seed-фраза: <code>{mnemonic}</code>"
        )

        await callback.message.answer(text=text, parse_mode="HTML")

    except Exception as e:
        await callback.message.answer(
            text=parser.get("wallet_info_error", error=str(e))
        )

    await callback.answer()


@router.callback_query(lambda c: c.data == "add_bitcoin_wallet")
async def add_bitcoin_wallet_handler(callback: CallbackQuery) -> None:
    wallet_name = f"bitcoin_wallet_{callback.from_user.id}_{int(time.time())}_{secrets.token_hex(4)}"
    new_wallet = bitcoin_implement.create_wallet(wallet_name)

    if new_wallet:
        db = await mongo_manager.get_database()
        wallets_collection = db["usdt_wallets"]

        wallet_doc = {
            "user_id": callback.from_user.id,
            "address": new_wallet["address"],
            "private_key": new_wallet["private_key"],
            "mnemonic": new_wallet["mnemonic"],
            "name": new_wallet["name"],
            "network": "bitcoin",
        }

        await wallets_collection.insert_one(wallet_doc)

        await callback.message.answer(
            text=parser.get("bitcoin_wallet_created")
            + f"\nАдрес: {new_wallet['address']}\n\n"
            + parser.get("security_warning")
            + "\n\n"
            + f"Seed-фраза: <code>{new_wallet['mnemonic']}</code>\n"
            + f"Приватный ключ (WIF): <code>{new_wallet['private_key']}</code>",
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(text=parser.get("wallet_creation_error"))

    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("wallet_info:"))
async def wallet_info_handler(callback: CallbackQuery) -> None:
    wallet_id = callback.data.split(":")[1]

    db = await mongo_manager.get_database()
    wallets_collection = db["usdt_wallets"]

    try:
        wallet = await wallets_collection.find_one(
            {
                "_id": ObjectId(wallet_id),
                "user_id": callback.from_user.id,
                "network": "bitcoin",
            }
        )

        if not wallet:
            await callback.message.answer(text=parser.get("wallet_not_found"))
            await callback.answer()
            return

        address = wallet.get("address", "Unknown")
        wallet_name = wallet.get("name", "Unknown")

        balance = bitcoin_implement.get_balance(wallet_name)

        text = (
            parser.get("wallet_information")
            + "\n\n"
            + f"Адрес: <code>{address}</code>\n"
            + f"BTC: {balance.get('btc', '0')}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=inline.get("transfer"),
                        callback_data=f"transfer:{wallet_id}",
                    ),
                    InlineKeyboardButton(
                        text=inline.get("top_up"), callback_data=f"top_up:{wallet_id}"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=inline.get("private_info"),
                        callback_data=f"private_info:{wallet_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=inline.get("back_to_wallets"),
                        callback_data="bitcoin_wallets",
                    )
                ],
            ]
        )

        await callback.message.answer(
            text=text, parse_mode="HTML", reply_markup=keyboard
        )

    except Exception as e:
        await callback.message.answer(
            text=parser.get("wallet_info_error", error=str(e))
        )

    await callback.answer()
