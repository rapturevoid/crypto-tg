from password_generator import PasswordGenerator
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.exceptions import AddressNotFound
from mnemonic import Mnemonic
from loguru import logger


class TronImplement:

    def __init__(self, network: str):
        self.tron = Tron(network=network)
        self.contract = (
            "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
            if network == "mainnet"
            else "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        )

    def convert_to_tron_amount(amount):
        return int(round(amount * 1_000_000))

    def create_wallet(self, strength=128):
        try:
            mnemo = Mnemonic("english")
            mnemonic_phrase = mnemo.generate(strength=strength)
            passgen = PasswordGenerator()
            passgen.minschars = 0
            passwd = passgen.generate()

            wallet = self.tron.generate_address_from_mnemonic(
                mnemonic_phrase, passphrase=passwd
            )
            logger.debug(
                "Generated new wallet: \n{adress}\n{private_key}\n{mnemonic}\n{passwd}",
                adress=wallet["base58check_address"],
                private_key=wallet["private_key"],  # [:4]
                mnemonic=mnemonic_phrase,  # [:13]
                passwd=passwd,
            )  # [:4]

            return {
                "adress": wallet["base58check_address"],
                "private_key": wallet["private_key"],
                "mnemonic": mnemonic_phrase,
                "passwd": passwd,
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

    def transfer(self, wallet: str, private_key: str, to: str, amount):
        contract = self.tron.get_contract(self.contract)
        try:
            smart_contract = (
                (
                    contract.functions.transfer(to, int(round(amount * 1_000_000)))
                    .with_owner(wallet)
                    .fee_limit(5_000_00)
                    .build()
                    .sign(PrivateKey(bytes.fromhex(private_key)))
                )
                .broadcast()
                .wait()
            )
            logger.debug(
                "Broadcasting smart contract: {contract}\n", contract=smart_contract
            )

        except Exception as e:
            logger.exception("Failed transfer!")


tron_implement = TronImplement("nile")