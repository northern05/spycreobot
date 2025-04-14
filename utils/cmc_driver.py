from datetime import datetime, timedelta
import requests


class CoinMarketCapDriver:
    def __init__(self, base_url: str, api_key: str):
        self.API_KEY = api_key
        self.BASE_URL = base_url
        self.headers = {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": self.API_KEY
        }

    def get_similar_tokens(self, symbol: str):
        """Fetches the top 10 most popular tokens similar to the given symbol, sorted by market cap."""
        url = f"{self.BASE_URL}/listings/latest"  # Fetches all tokens with market cap data
        response = requests.get(url, headers=self.headers, params={"limit": 5000})  # Fetch top 500 tokens

        if response.status_code != 200:
            return {"error": "Failed to fetch data from CoinMarketCap"}

        data = response.json().get("data", [])

        # Filter tokens that have the entered symbol in their name or symbol
        similar_tokens = [
            {
                "name": token["name"],
                "symbol": token["symbol"],
                "market_cap": token["quote"]["USD"]["market_cap"],  # Get market cap
                "image_url": f"https://s2.coinmarketcap.com/static/img/coins/64x64/{token['id']}.png"
            }
            for token in data if symbol.lower() in token["symbol"].lower() or symbol.lower() in token["name"].lower()
        ]

        # Sort by market capitalization and return top 10
        top_similar_tokens = sorted(similar_tokens, key=lambda x: x["market_cap"], reverse=True)[:10]
        return top_similar_tokens

    def get_current_token_price(self, symbol: str):
        """Fetches the current price of a given token by its symbol."""

        # Step 1: Get token ID from symbol
        url = f"{self.BASE_URL}/map"
        response = requests.get(url, headers=self.headers)

        if response.status_code != 200:
            return {"error": "Failed to fetch token data"}

        data = response.json().get("data", [])

        # Find the exact match for the token symbol
        token = next((t for t in data if t["symbol"].upper() == symbol.upper()), None)

        if not token:
            return {"error": f"Token '{symbol}' not found"}

        token_id = token["id"]

        # Step 2: Fetch the token's price
        price_url = f"{self.BASE_URL}/quotes/latest?id={token_id}"
        price_response = requests.get(price_url, headers=self.headers)

        if price_response.status_code != 200:
            return {"error": "Failed to fetch token price"}

        price_data = price_response.json().get("data", {}).get(str(token_id), {})
        price_usd = price_data.get("quote", {}).get("USD", {}).get("price", "N/A")

        return {
            "name": token["name"],
            "symbol": token["symbol"],
            "price_usd": price_usd
        }


if __name__ == '__main__':
    # Example Usage:
    cmc_driver = CoinMarketCapDriver()
    result = cmc_driver.get_similar_tokens("BTC")
    print(result)
