import os

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


config = Config()
db_config = DBSettings()
redis_config = RedisSettings()
