import httpx


class TronWalletDriver:

    def __init__(self, base_url: str, usdt_address: str):
        self.BASE_URL = base_url
        self.USDT_CONTRACT = usdt_address
        self.client = httpx.AsyncClient()

    async def get_balance(self, address: str) -> float:
        """Returns TRX balance in float (converted from SUN)."""
        url = f"{self.BASE_URL}/v1/accounts/{address}"
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()

        if not data.get("data"):
            return 0.0

        balance_sun = data["data"][0].get("balance", 0)
        return balance_sun / 1_000_000  # Convert SUN to TRX

    async def get_usdt_balance(self, address: str) -> float:
        """Returns USDT (TRC20) token balance."""
        url = f"{self.BASE_URL}/v1/accounts/{address}/transactions/trc20"
        params = {"limit": 200, "only_confirmed": "true", "contract_address": self.USDT_CONTRACT}
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        transfers = response.json().get("data", [])

        balance = 0
        for tx in transfers:
            if tx.get("to_address") == address:
                balance += int(tx.get("value", 0))
            elif tx.get("from_address") == address:
                balance -= int(tx.get("value", 0))

        return balance / 10**6  # USDT has 6 decimals

    async def get_transactions(self, address: str, limit: int = 10) -> list:
        """Returns last transactions for the given address."""
        url = f"{self.BASE_URL}/v1/accounts/{address}/transactions/trc20"
        params = {"limit": limit}
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        response = []
        if not data: return []
        for tx in data:
            tx_hash = tx.get("transaction_id")
            amount = int(tx["value"]) / (10 ** int(tx["token_info"].get("decimals", 6)))
            token_address = tx["token_info"]["address"]
            from_address = tx.get("from")
            symbol = tx["token_info"].get("symbol", "")
            created_at = tx.get("block_timestamp")
            if token_address == "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t":
                response.append({"tx_hash": tx_hash, "amount": amount, "from_address": from_address, "created_at": created_at})

        return data.get("data", [])

    async def close(self):
        await self.client.aclose()


# Example usage:
import asyncio


async def main():
    driver = TronWalletDriver(
        base_url="https://api.trongrid.io",
        usdt_address="TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj"
    )
    wallet = "TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9"

    trx_balance = await driver.get_balance(wallet)
    usdt_balance = await driver.get_usdt_balance(wallet)
    print(f"TRX Balance: {trx_balance} TRX")
    print(f"USDT Balance: {usdt_balance} USDT")

    txs = await driver.get_transactions(wallet)
    print(txs)
    await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
