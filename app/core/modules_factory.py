from redis.asyncio import Redis
from app.core.config import redis_config, fb_config, crypto_config
from utils.facebook_driver import FacebookAdsLibraryDriver
from utils.wallet_driver import TronWalletDriver

# -------- Initialize REDIS connection ----------------------
redis_db = Redis(
    host=redis_config.REDIS_HOST,
    port=redis_config.REDIS_PORT,
    username=redis_config.REDIS_USER,
    password=redis_config.REDIS_PASSWORD
)

# ----------------- Initialize Facebook ----------------------
fb_driver = FacebookAdsLibraryDriver(
    app_id=fb_config.APP_ID,
    app_secret=fb_config.APP_SECRET,
    access_token=fb_config.ACCESS_TOKEN,
    api_url=fb_config.API_URL
)

# ----------- Initialize Wallet Driver ----------------------
wallet_driver = TronWalletDriver(base_url=crypto_config.TRON_API_URL, usdt_address=crypto_config.USDT_CONTRACT)
