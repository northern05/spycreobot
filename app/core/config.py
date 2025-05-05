import os

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    api_v1_prefix: str = "/portfolio_tracker/api/v1"


class RedisSettings(BaseSettings):
    REDIS_HOST: str = os.environ.get('REDIS_HOST', "195.189.60.233")
    REDIS_PORT: str = os.environ.get('REDIS_PORT', "6379")
    REDIS_USER: str = os.environ.get('REDIS_USER', "ai-agent-user")
    REDIS_PASSWORD: str = os.environ.get('REDIS_PASSWORD', "ai-agent-password")
    REDIS_URL: str = f"redis://{REDIS_USER}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"


class DBSettings(BaseSettings):
    DB_NAME: str = os.environ.get("DB_NAME", "ai-agent-dev")
    DB_USER: str = os.environ.get("DB_USER", "ai-agent-user")
    DB_HOST: str = os.environ.get("DB_HOST", "195.189.60.233")
    DB_PORT: str = os.environ.get("DB_PORT", "5432")
    DB_PW: str = os.environ.get("DB_PW", "ai-agent-password")

    SQLALCHEMY_DATABASE_URL: str = (
        f"postgresql+asyncpg://{DB_USER}:{DB_PW}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    db_echo: bool = False


class CryptoSettings(BaseSettings):
    MASTER_WALLET: str = os.environ.get("MASTER_WALLET", "")
    TRON_API_URL: str = os.environ.get("TRON_API_URL", "https://api.trongrid.io")
    USDT_CONTRACT: str = os.environ.get("USDT_CONTRACT", "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj")


class FacebookSettings(BaseSettings):
    API_URL: str = os.environ.get("API_URL", "https://graph.facebook.com/v19.0/ads_archive")
    ACCESS_TOKEN: str = os.environ.get("ACCESS_TOKEN",
                                       "EAAKCNpvlGQ8BO2MKCB3UOGJiF4kgya3SeWkK7R1uCkD4AlFmqkbD4Ox2AG9xZAbcpR6QkEDnJ6yBJFWrkR8SIU3RWSZAQaP5PMEO6Fi1hAg7pdja79L0vxfFDhFGUag24ls2VvNOQuEJbcbo93qGBI2PW7InOZAe3m2FAl3ZCUMl8nrBIqCgkenlBDRM6XwdQZC2OseS5kwtFRIYBEZCVu2cg55j1IgXEeZAAZDZD")
    APP_ID: str = os.environ.get("APP_ID", "706121008748815")
    APP_SECRET: str = os.environ.get("APP_SECRET", "aff7dc896abd538f8e8050102bbbc793")


config = Config()
db_config = DBSettings()
redis_config = RedisSettings()
fb_config = FacebookSettings()
crypto_config = CryptoSettings()
