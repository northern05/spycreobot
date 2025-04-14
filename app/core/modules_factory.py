from redis.asyncio import Redis
from app.core.config import cmc_config, perplexity_config, elfa_config, redis_config, llama_config, \
    twitter_account_config
from utils.cmc_driver import CoinMarketCapDriver
from utils.perplexity_driver import PerplexityDriver
from utils.elfa_driver import ElfaDriver
from utils.coingecko_driver import CryptoPriceFetcher
from utils.llama_driver import LlamaDriver
from utils.twikit_driver import TwitterScraper

# -------- Initialize CoinMarketCap Driver -----------------
cmc_driver = CoinMarketCapDriver(
    base_url=cmc_config.CMC_URL,
    api_key=cmc_config.CMC_API_KEY
)

# -------- Initialize Perplexity Driver ---------------------
perplexity_driver = PerplexityDriver(
    base_url=perplexity_config.PERPLEXITY_URL,
    api_key=perplexity_config.PERPLEXITY_API_KEY
)

# -------- Initialize Elfa Driver ---------------------------
elfa_driver = ElfaDriver(
    base_url=elfa_config.ELFA_URL,
    api_key=elfa_config.ELFA_API_KEY
)

# ---------- Initialize CoinGecko Driver --------------------
coin_gecko_driver = CryptoPriceFetcher()

# -------- Initialize REDIS connection ----------------------
redis_db = Redis(
    host=redis_config.REDIS_HOST,
    port=redis_config.REDIS_PORT,
    username=redis_config.REDIS_USER,
    password=redis_config.REDIS_PASSWORD
)

# -------- Initialize Llama connection -----------------------
llama = LlamaDriver(base_url=llama_config.LLAMA_URL)

# --------- Initialize Twitter Scraper -----------------------
twitter_scraper = TwitterScraper(
    accounts=twitter_account_config.ACCOUNTS
)
