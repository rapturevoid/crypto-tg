from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)
from src.string_parser.string_parser import inline, parser
from src.mongo_manager.mongo_manager import mongo_manager
from src.crypto_impl.tron import tron_implement
from bson import ObjectId
import secrets
import string

router = Router()

transfer_states = {}
add_wallet_states = {}


@router.callback_query(lambda c: c.data == "tron_wallets")
async def tron_wallets_handler(callback: CallbackQuery) -> None:
    db = await mongo_manager.get_database()
    usdt_wallets = db["usdt_wallets"]

    user_wallets = await usdt_wallets.find({"user_id": callback.from_user.id}).to_list(
        length=None
    )

    if not user_wallets:
        text = parser.get("no_tron_wallets")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=inline.get("add_wallet"), callback_data="add_tron_wallet"
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
            name = wallet.get("name", "")
            address = wallet.get("address", "Unknown")
            wallet_id = str(wallet.get("_id"))
            display_name = (
                name
                if name
                else (
                    address[:6] + "..." + address[-4:] if len(address) > 10 else address
                )
            )
            wallet_buttons.append(
                InlineKeyboardButton(
                    text=display_name, callback_data=f"wallet_info:{wallet_id}"
                )
            )

        keyboard_rows = []
        for i in range(0, len(wallet_buttons), 2):
            row = wallet_buttons[i : i + 2]
            keyboard_rows.append(row)

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=inline.get("add_wallet"), callback_data="add_tron_wallet"
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

    if user_id in add_wallet_states:
        wallet_name = message.text.strip()
        if not wallet_name:
            await message.answer(
                text="Название кошелька не может быть пустым. Введите название:",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Отмена", callback_data="cancel_add_wallet"
                            )
                        ]
                    ]
                ),
            )
            return

        # Create wallet
        new_wallet = tron_implement.create_wallet()

        if new_wallet:
            db = await mongo_manager.get_database()
            usdt_wallets = db["usdt_wallets"]

            wallet_doc = {
                "user_id": user_id,
                "address": new_wallet["address"],
                "private_key": new_wallet["private_key"],
                "mnemonic": new_wallet["mnemonic"],
                "passwd": new_wallet["passwd"],
                "network": "tron",
                "name": wallet_name,
            }

            await usdt_wallets.insert_one(wallet_doc)

            await message.answer(
                text=parser.get("wallet_created")
                + f"\nНазвание: {wallet_name}\n"
                + f"Адрес: {new_wallet['address']}\n\n"
                + parser.get("security_warning")
                + "\n\n"
                + f"Seed-фраза: <code>{new_wallet['mnemonic']}</code>\n"
                + f"Приватный ключ: <code>{new_wallet['private_key']}</code>",
                parse_mode="HTML",
            )
        else:
            await message.answer(text=parser.get("wallet_creation_error"))

        del add_wallet_states[user_id]
        return

    if user_id not in transfer_states:
        return

    state = transfer_states[user_id]

    if state["step"] == "address":
        address = message.text.strip()
        if not address.startswith("T") or len(address) != 34:
            await message.answer(
                text=parser.get("invalid_address_format"),
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
        state["step"] = "currency"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="TRX", callback_data="select_currency:TRX"
                    ),
                    InlineKeyboardButton(
                        text="USDT", callback_data="select_currency:USDT"
                    ),
                ],
                [InlineKeyboardButton(text="Отмена", callback_data="cancel_transfer")],
            ]
        )

        await message.answer(text=parser.get("select_currency"), reply_markup=keyboard)

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


@router.callback_query(lambda c: c.data.startswith("select_currency:"))
async def select_currency_handler(callback: CallbackQuery) -> None:
    if callback.from_user.id not in transfer_states:
        await callback.answer()
        return

    currency = callback.data.split(":")[1]
    transfer_states[callback.from_user.id]["currency"] = currency
    transfer_states[callback.from_user.id]["step"] = "amount"

    await callback.message.answer(
        text=parser.get("enter_transfer_amount", currency=currency),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Отмена", callback_data="cancel_transfer")]
            ]
        ),
    )
    await callback.answer()


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
    currency = state["currency"]

    try:
        db = await mongo_manager.get_database()
        usdt_wallets = db["usdt_wallets"]

        wallet = await usdt_wallets.find_one(
            {"_id": ObjectId(wallet_id), "user_id": user_id}
        )

        if not wallet:
            await message.answer(text=parser.get("wallet_not_found"))
            return

        sender_address = wallet["address"]
        private_key = wallet["private_key"]

        if currency == "TRX":
            transfer_amount = amount
        else:
            transfer_amount = amount

        tx_hash, scan_url = tron_implement.transfer(
            wallet=sender_address,
            private_key=private_key,
            to=recipient_address,
            amount=transfer_amount,
            currency=currency,
        )

        tronscan_url = f"{scan_url}/#/transaction/{tx_hash}"

        await message.answer(
            text=parser.get("transfer_success") + f"\n\n"
            f"Получатель: <code>{recipient_address}</code>\n"
            f"Сумма: {amount} {currency}\n"
            f"Хеш транзакции: <code>{tx_hash}</code>\n\n"
            f"Посмотреть на TronScan: {tronscan_url}",
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
    usdt_wallets = db["usdt_wallets"]

    try:
        wallet = await usdt_wallets.find_one(
            {"_id": ObjectId(wallet_id), "user_id": callback.from_user.id}
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
            + f"Приватный ключ: <code>{private_key}</code>\n\n"
            + f"Seed-фраза: <code>{mnemonic}</code>"
        )

        await callback.message.answer(text=text, parse_mode="HTML")

    except Exception as e:
        await callback.message.answer(
            text=parser.get("wallet_info_error", error=str(e))
        )

    await callback.answer()


@router.callback_query(lambda c: c.data == "add_tron_wallet")
async def add_tron_wallet_handler(callback: CallbackQuery) -> None:
    add_wallet_states[callback.from_user.id] = True

    await callback.message.answer(
        text="Введите название для нового Tron кошелька:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Отмена", callback_data="cancel_add_wallet")]
            ]
        ),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel_add_wallet")
async def cancel_add_wallet_handler(callback: CallbackQuery) -> None:
    if callback.from_user.id in add_wallet_states:
        del add_wallet_states[callback.from_user.id]

    await callback.message.answer(text="Создание кошелька отменено.")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("wallet_info:"))
async def wallet_info_handler(callback: CallbackQuery) -> None:
    wallet_id = callback.data.split(":")[1]

    db = await mongo_manager.get_database()
    usdt_wallets = db["usdt_wallets"]

    try:
        wallet = await usdt_wallets.find_one(
            {"_id": ObjectId(wallet_id), "user_id": callback.from_user.id}
        )

        if not wallet:
            await callback.message.answer(text=parser.get("wallet_not_found"))
            await callback.answer()
            return

        address = wallet.get("address", "Unknown")

        balance = tron_implement.get_balance(address)

        text = (
            parser.get("wallet_information")
            + "\n\n"
            + f"Адрес: <code>{address}</code>\n"
            + f"TRX: {balance.get('trx', '0')}\n"
            + f"USDT: {balance.get('usdt', '0')}"
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
                        text=inline.get("back_to_wallets"), callback_data="tron_wallets"
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
