from eth_typing import Hash32
from web3 import Web3


class CryptoDriver:

    def __init__(self, web3_rpc: str, master_wallet: str):
        self.w3 = Web3(Web3.HTTPProvider(web3_rpc))
        self.usdt_contract_address = ""
        self.master_wallet = Web3.to_checksum_address(master_wallet)
        self.ERC20_ABI = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]

    def get_latest_block(self):
        return self.w3.eth.get_block('latest')

    def get_token_balance(self, token_address: str, wallet_address: str):
        """Get token balance for an address"""
        token_contract = self.w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=self.ERC20_ABI)
        balance = token_contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        return balance

    def get_transactions(self, address: str, start_block: int):
        latest_block = self.get_latest_block().number
        if not start_block or start_block < latest_block - 999:
            start_block = latest_block - 999
        transactions = []
        for i in range(start_block, latest_block):
            block = self.w3.eth.get_block(i, full_transactions=True)
            for tx in block['transactions']:
                if tx['to'] == self.master_wallet or tx['from'] == address:
                    transactions.append(tx)
        return transactions

    def get_transaction_details(self, tx_hash: Hash32):
        receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        print(receipt)
