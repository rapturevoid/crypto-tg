from password_generator import generate
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.exceptions import AddressNotFound
from mnemonic import Mnemonic
from loguru import logger
import os


class TronImplement:

    def __init__(self, network: str):
        logger.info(f"Initializing TronImplementation with network: {network}")
        self.tron = Tron(network=network)
        self.contract = (
            "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
            if network == "mainnet"
            else "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        )
        self.scan_url = (
            "https://tronscan.org"
            if network == "mainnet"
            else "https://nile.tronscan.org"
        )

    def create_wallet(self, name: str, strength: int = 256):
        try:
            mnemo = Mnemonic("english")
            mnemonic_phrase = mnemo.generate(strength=strength)
            passwd = generate()

            wallet = self.tron.generate_address_from_mnemonic(
                mnemonic_phrase, passphrase=passwd
            )
            return {
                "address": wallet["base58check_address"],
                "private_key": wallet["private_key"],
                "mnemonic": mnemonic_phrase,
                "passwd": passwd,
                "name": name,
            }
        except Exception:
            logger.exception("Generate wallet error!")

    def get_balance(self, wallet: str):
        try:
            trx_balance = self.tron.get_account_balance(addr=wallet)
            contract = self.tron.get_contract(self.contract)
            usdt_balance = (
                contract.functions.balanceOf(wallet)
                / 10 ** contract.functions.decimals()
            )

            logger.debug(
                "Getting balance of {wallet}: TRX: {trx}, USDT: {usdt}",
                wallet=wallet,
                trx=trx_balance,
                usdt=usdt_balance,
            )

            return {"trx": trx_balance, "usdt": usdt_balance}

        except AddressNotFound:
            logger.warning(
                "Address {wallet} not found on chain or balance is zero", wallet=wallet
            )
            return {"trx": "0", "usdt": "0"}
        except Exception:
            logger.exception("Balance getting error!")
            return {"trx": "0", "usdt": "0"}

    def transfer(
        self, wallet: str, private_key: str, to: str, amount, currency: str = "USDT"
    ):
        try:
            if currency == "USDT":
                contract = self.tron.get_contract(self.contract)
                amount_in_smallest = int(round(amount * 1_000_000))

                txn = (
                    contract.functions.transfer(to, amount_in_smallest)
                    .with_owner(wallet)
                    .fee_limit(5_000_000)
                    .build()
                    .sign(PrivateKey(bytes.fromhex(private_key)))
                )
            elif currency == "TRX":
                amount_in_sun = int(round(amount * 1_000_000))

                txn = (
                    self.tron.trx.transfer(wallet, to, amount_in_sun)
                    .build()
                    .sign(PrivateKey(bytes.fromhex(private_key)))
                )
            else:
                raise ValueError(f"Unsupported currency: {currency}")

            result = txn.broadcast().wait()

            tx_hash = result["id"] if isinstance(result, dict) else str(result.txID)

            logger.debug(
                "Transfer completed: {hash}, amount: {amount} {currency}",
                hash=tx_hash,
                amount=amount,
                currency=currency,
            )

            return tx_hash, self.scan_url

        except Exception as e:
            logger.exception("Failed transfer!")
            raise


tron_implement = TronImplement(os.getenv("TRON_NETWORK", "nile"))
