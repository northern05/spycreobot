from redis.asyncio import Redis
from app.core.config import redis_config

# -------- Initialize REDIS connection ----------------------
redis_db = Redis(
    host=redis_config.REDIS_HOST,
    port=redis_config.REDIS_PORT,
    username=redis_config.REDIS_USER,
    password=redis_config.REDIS_PASSWORD
)
