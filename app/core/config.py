import os

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    api_v1_prefix: str = "/bot/api/v1"


class RedisSettings(BaseSettings):
    REDIS_HOST: str = os.environ.get('REDIS_HOST')
    REDIS_PORT: str = os.environ.get('REDIS_PORT')
    REDIS_USER: str = os.environ.get('REDIS_USER')
    REDIS_PASSWORD: str = os.environ.get('REDIS_PASSWORD')
    REDIS_URL: str = f"redis://{REDIS_USER}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"


class DBSettings(BaseSettings):
    DB_NAME: str = os.environ.get("DB_NAME")
    DB_USER: str = os.environ.get("DB_USER")
    DB_HOST: str = os.environ.get("DB_HOST")
    DB_PORT: str = os.environ.get("DB_PORT")
    DB_PW: str = os.environ.get("DB_PW")

    SQLALCHEMY_DATABASE_URL: str = (
        f"postgresql+asyncpg://{DB_USER}:{DB_PW}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    db_echo: bool = False


class CryptoSettings(BaseSettings):
    MASTER_WALLET: str = os.environ.get("MASTER_WALLET")
    TRON_API_URL: str = os.environ.get("TRON_API_URL") #"https://api.trongrid.io"
    USDT_CONTRACT: str = os.environ.get("USDT_CONTRACT")


class FacebookSettings(BaseSettings):
    API_URL: str = os.environ.get("API_URL", "https://graph.facebook.com/v19.0/ads_archive")
    ACCESS_TOKEN: str = os.environ.get("ACCESS_TOKEN")
    APP_ID: str = os.environ.get("APP_ID")
    APP_SECRET: str = os.environ.get("APP_SECRET")


config = Config()
db_config = DBSettings()
redis_config = RedisSettings()
fb_config = FacebookSettings()
crypto_config = CryptoSettings()
