import os
import json

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    api_v1_prefix: str = "/portfolio_tracker/api/v1"
    APP_DOMAIN: str = "api.agent.zpoken.dev"


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


class CoinMarketCapSettings(BaseSettings):
    CMC_URL: str = os.environ.get("CMC_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency")
    CMC_API_KEY: str = os.environ.get("CMC_API_KEY", "54feb766-7b6e-4754-8592-b5bc463e2c2a")


class ElfaSettings(BaseSettings):
    ELFA_URL: str = os.environ.get("ELFA_URL", "https://api.elfa.ai/v1")
    ELFA_API_KEY: str = os.environ.get("ELFA_API_KEY", "elfak_db1eb0fe5cadbee7f798e2f79f5c53b8bfddb7d5")


class PerplexitySettings(BaseSettings):
    PERPLEXITY_URL: str = os.environ.get("PERPLEXITY_URL", "https://api.perplexity.ai")
    PERPLEXITY_API_KEY: str = os.environ.get("PERPLEXITY_API_KEY",
                                             "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")


class TwitterCredentialsSettings(BaseSettings):
    accounts: str = os.environ.get("TWITTER_ACCOUNTS", '''[{"username": "GShimko38911", "email": "glib@zpoken.io", "password": "y5iwbGq=/nX:'CL"}, {"username": "GlebShimko", "email": "gleb5shimko@gmail.com", "password": "MU#?<_3Bf2iwU6M"}, {"username": "yur35494", "email": "yura@zpoken.io", "password": "213456qaZ"}]''')
    ACCOUNTS: list = json.loads(accounts)


class LLamaSettings(BaseSettings):
    LLAMA_URL: str = os.environ.get("LLAMA_URL", "http://195.189.60.154:8000/generate")


config = Config()
db_config = DBSettings()
cmc_config = CoinMarketCapSettings()
elfa_config = ElfaSettings()
perplexity_config = PerplexitySettings()
redis_config = RedisSettings()
llama_config = LLamaSettings()
twitter_account_config = TwitterCredentialsSettings()
