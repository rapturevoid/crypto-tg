from bitcoinlib.wallets import Wallet
from bitcoinlib.networks import Network
from loguru import logger


class BitcoinImplementation:
    def __init__(self):
        self.scan_url = "https://mempool.space/ru/tx/"

    def create_wallet(self, name: str):
        try:
            wallet = Wallet.create(name, network="bitcoin")
            key = wallet.get_key()
            mnemonic_phrase = wallet.mnemonic()
            return {
                "address": key.address,
                "private_key": key.wif,
                "mnemonic": mnemonic_phrase,
                "name": name,
            }
        except Exception as e:
            logger.exception("Generate wallet error!")

    def get_balance(self, wallet_name: str):
        try:
            wallet = Wallet(wallet_name)
            balance = wallet.balance()
            logger.debug(
                "Getting balance of {wallet}: BTC: {balance}",
                wallet=wallet_name,
                balance=balance,
            )
            return {"btc": balance}
        except Exception as e:
            logger.exception(
                "Error getting balance for wallet: {wallet}", wallet=wallet_name
            )
            return {"btc": "0"}

    def transfer(
        self, wallet_name: str, to_address: str, amount: float, fee: float = 0.0001
    ):
        try:
            wallet = Wallet(wallet_name)
            tx = wallet.send_to(to_address, amount, fee=fee)
            logger.debug(
                "Transferred {amount} BTC from {wallet} to {to_address}. TXID: {txid}",
                amount=amount,
                wallet=wallet_name,
                to_address=to_address,
                txid=tx.txid,
            )
            return {"txid": tx.txid, "link": f"{self.scan_url}{tx.txid}"}
        except Exception as e:
            logger.exception(
                "Transfer error from wallet: {wallet} to address: {to_address}",
                wallet=wallet_name,
                to_address=to_address,
            )


bitcoin_implement = BitcoinImplementation()
