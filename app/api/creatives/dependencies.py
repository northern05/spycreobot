import logging
import hashlib
import json
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.credits import dependencies as credits_dp
from app.core.models import db_helper
from .schemas import CreativeResponse, CreativeRequest
from app.core.modules_factory import fb_driver, redis_db

CACHE_TTL_SECONDS = 3600


async def get_creatives(
        creative_request: CreativeRequest,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> dict:
    cache_key_params = creative_request.dict(exclude={"telegram_id"}, exclude_none=True)
    if 'placements' in cache_key_params and cache_key_params['placements'] is not None:
        cache_key_params['placements'] = sorted(cache_key_params['placements'])
    if 'search_cursor' in cache_key_params and cache_key_params['search_cursor'] is not None:
        cache_key_params['search_cursor'] = json.dumps(cache_key_params['search_cursor'], sort_keys=True)

    cache_key_string = json.dumps(cache_key_params, sort_keys=True)
    cache_key_hash = hashlib.sha256(cache_key_string.encode('utf-8')).hexdigest()
    redis_key = f"creatives_cache:{cache_key_hash}"

    cached_data = await redis_db.get(redis_key)
    if cached_data:
        logging.info(f"Cache hit for key: {redis_key}")
        try:
            cached_result = json.loads(cached_data.decode('utf-8'))
            ads = [CreativeResponse.model_validate(ad_data) for ad_data in cached_result.get("ads", [])]
            search_cursor = cached_result.get("search_cursor")
            return {"ads": ads, "after": search_cursor}
        except Exception as e:
            logging.error(f"Failed to deserialize cached data for {redis_key}: {e}. Fetching new data.")

    logging.info(f"Cache miss for key: {redis_key}. Fetching from Facebook...")

    ads, search_cursor = await fb_driver.get_ads_page(
        **creative_request.dict(exclude={"telegram_id"})
    )
    result = [CreativeResponse.model_validate(ad) for ad in ads]
    if result:
        await credits_dp.process_users_credits(session=session, telegram_id=creative_request.telegram_id)
        data_to_cache = {
            "ads": [ad.model_dump() for ad in result],
            "search_cursor": search_cursor
        }
        await redis_db.setex(redis_key, CACHE_TTL_SECONDS, json.dumps(data_to_cache))
        logging.info(f"Data cached for key: {redis_key} with TTL: {CACHE_TTL_SECONDS}s")

    return {"ads": result, "after": search_cursor}
