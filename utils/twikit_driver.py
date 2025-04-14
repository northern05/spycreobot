import json
import asyncio
import logging

from twikit import Client, TooManyRequests, UserNotFound, Unauthorized, AccountSuspended
from datetime import datetime, timedelta, timezone
import random


class TwitterScraper:
    def __init__(self, accounts: list, min_tweets: int = 10):
        self.accounts = accounts
        self.clients = {}
        self.min_tweets = min_tweets
        self.login_states = {}
        self.default_language = "en-US"
        self.client_initialized = False

    async def initialize_clients(self):
        """Initializes clients and attempts login for each account."""
        for account in self.accounts:
            try:
                client = Client(language=self.default_language)
                await client.login(auth_info_1=account['username'], auth_info_2=account['email'],
                                   password=account['password'])
                client.save_cookies(f"cookies_{account['username']}.json")  # Save cookies uniquely
                client.load_cookies(f"cookies_{account['username']}.json")  # Load saved cookies
                self.clients[account['username']] = client
                self.login_states[account['username']] = True
                logging.info(f"Successfully logged in with account: {account['username']}")
            except Exception as e:
                logging.error(f"Failed to login with account {account['username']}: {e}")
                self.clients[account['username']] = None  # Mark as failed
                self.login_states[account['username']] = False

    async def get_client(self):
        """Returns an available client (or None if none is available)."""
        available_clients = [username for username, logged_in in self.login_states.items() if logged_in]
        if available_clients:
            return self.clients[random.choice(available_clients)]  # Return a random available client
        else:
            return None

    async def retry_login(self, username):
        """Attempts to re-login with a specific account."""
        account = next((acc for acc in self.accounts if acc['username'] == username), None)
        if account:
            try:
                client = self.clients[username]
                await client.login(auth_info_1=account['username'], auth_info_2=account['email'],
                                   password=account['password'])
                client.save_cookies(f"cookies_{account['username']}.json")
                client.load_cookies(f"cookies_{account['username']}.json")
                self.login_states[username] = True
                logging.info(f"Successfully re-logged in with account: {username}")
                return True
            except Exception as e:
                logging.error(f"Failed to re-login with account {username}: {e}")
                self.login_states[username] = False
                return False
        else:
            logging.error(f"Account {username} not found for re-login.")
            return False

    async def get_tweets(self, user_id: str, tweets):
        """Retrieve tweets using Twikit."""
        current_client = await self.get_client()

        if tweets is None:
            logging.info(f"{datetime.now()} - Fetching initial tweets...")
            tweets = await current_client.get_user_tweets(user_id=user_id, tweet_type='Tweets', count=3)
        else:
            wait_time = random.randint(5, 10)
            logging.info(f"{datetime.now()} - Fetching next tweets after {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            tweets = await tweets.next()

        return tweets

    async def get_user_id_by_username(self, username: str):
        if not self.client_initialized:
            await self.initialize_clients()
        current_client = await self.get_client()
        user = await current_client.get_user_by_screen_name(screen_name=username)
        return user.id

    async def get_username_by_user_id(self, user_id: str):
        if not self.client_initialized:
            await self.initialize_clients()
        current_client = await self.get_client()
        user = await current_client.get_user_by_id(user_id=user_id)
        return user.screen_name

    async def fetch_tweets(self, protocol_name: str):
        if not self.client_initialized:
            await self.initialize_clients()  # Ensure clients are initialized

        tweet_data = []
        tweets = None
        current_client = await self.get_client()

        if not current_client:
            logging.error("No available Twitter accounts to fetch tweets.")
            return None

        while True:
            try:
                user_id = await self.get_user_id_by_username(username=protocol_name)
                tweets = await self.get_tweets(tweets=tweets, user_id=user_id)
            except TooManyRequests as e:
                logging.warning(f"Rate limit exceeded on account. Trying another account.")
                self.login_states[
                    next((acc['username'] for acc in self.accounts if self.clients[acc['username']] == current_client),
                         None)] = False  # Mark the current client as logged out
                current_client = await self.get_client()  # Get a new client
                if not current_client:
                    logging.error("No more available accounts to retry.")
                    return None  # No more accounts to try
                await self.retry_login(
                    next((acc['username'] for acc in self.accounts if self.clients[acc['username']] == current_client),
                         None))
                continue  # Retry the loop with the new client

            except UserNotFound as e:
                logging.error(f"{protocol_name} not exists.")
                return None
            except Unauthorized as e:
                logging.warning(f"Unauthorized access. Trying to re-login.")
                self.login_states[
                    next((acc['username'] for acc in self.accounts if self.clients[acc['username']] == current_client),
                         None)] = False  # Mark the current client as logged out
                current_client = await self.get_client()
                if not current_client:
                    logging.error("No more available accounts to retry.")
                    return None
                await self.retry_login(
                    next((acc['username'] for acc in self.accounts if self.clients[acc['username']] == current_client),
                         None))
                continue
            except AccountSuspended as e:
                logging.error(f"Account suspended: {e}")
                self.login_states[
                    next((acc['username'] for acc in self.accounts if self.clients[acc['username']] == current_client),
                         None)] = False  # Mark the current client as logged out
                current_client = await self.get_client()
                if not current_client:
                    logging.error("No more available accounts to retry.")
                    return None
                await self.retry_login(
                    next((acc['username'] for acc in self.accounts if self.clients[acc['username']] == current_client),
                         None))
                continue

            if not tweets and not tweet_data:
                logging.info(f"{datetime.now()} - No more tweets found")
                return None

            last_tweet_date = None
            for tweet in tweets:
                last_tweet_date = datetime.strptime(tweet.created_at, "%a %b %d %H:%M:%S %z %Y")
                if last_tweet_date > (datetime.now(timezone.utc) - timedelta(days=7)):
                    tweet_data.append({"content": tweet.text,
                                       "created_at": tweet.created_at,
                                       "retweets": tweet.retweet_count,
                                       "likes": tweet.favorite_count})
            if last_tweet_date < (datetime.now(timezone.utc) - timedelta(days=1)):
                break

        return tweet_data


if __name__ == "__main__":
    async def run():
        urls = ["x.com/Bitcoin",
                "x.com/ethereum",
                "x.com/Tether_to",
                "x.com/ripple",
                "x.com/bnbchain",
                "x.com/solana",
                "x.com/wormhole",
                "https://x.com/Aptos_Network",
                "https://x.com/apecoin",
                "https://x.com/Starknet",
                "https://x.com/JupiterExchange",
                "https://x.com/virtuals_io",
                "https://x.com/ssv_network",
                "https://twitter.com/nearprotocol",
                "https://twitter.com/aave"]
        accounts = [

        ]
        scraper = TwitterScraper(
            accounts=accounts,
            min_tweets=10,
        )
        with open("data.txt", "a", encoding="utf-8") as file:
            for url in urls:
                protocol_name = url.split("/")[-1]
                results = await scraper.fetch_tweets(protocol_name=protocol_name)
                file.write(protocol_name + "\n")
                file.write("=" * 100 + "\n")
                file.write(json.dumps(results, indent=4, ensure_ascii=False))
                file.write("\n\n")
                print(results)
                await asyncio.sleep(5)


    asyncio.run(run())
