import asyncio
import logging
import hashlib
import json
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.credits import dependencies as credits_dp
from app.core.models import db_helper
from .schemas import CreativeResponse, CreativeRequest
from app.core.modules_factory import fb_driver, redis_db
from utils.const import *

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


async def update_all_creatives(
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    combination_tasks = []
    for geo in COUNTRY_TO_LANG_CODE.keys():
        for ad_type in ("image", "video", "all"):
            for period in ("week", "month", "quarter", "halfyear"):
                _search_cursor = None
                for i in range(5):
                    base_request_params = {
                        "telegram_id": "0",
                        "niche": "gambling",
                        "placements": ["instagram", "facebook", "audience_network", "threads", "messenger"],
                        "country": geo,
                        "ad_type": ad_type,
                        "period": period,
                        "keyword": None,
                        "search_cursor": _search_cursor
                    }
                    creative_request_model = CreativeRequest(**base_request_params)

                    # Launch a sub-task for this specific combination to fetch multiple pages
                    # This avoids deep nesting and makes it truly async
                    async def _fetch_and_cache_pages_for_combination(
                            req_model: CreativeRequest, current_session: AsyncSession, pages_to_cache: int = 5
                    ):
                        search_cursor_for_combo = None
                        for page_num in range(pages_to_cache):
                            try:
                                # Create a copy of the request model and update cursor
                                page_request_model = req_model.copy(update={"search_cursor": search_cursor_for_combo})

                                logging.info(
                                    f"Caching: Niche={req_model.niche}, Country={req_model.country}, Type={req_model.ad_type}, Period={req_model.period}, Keyword={req_model.keyword}, Page={page_num + 1}")

                                # Call get_creatives directly (it handles fetching from FB or cache, and caching)
                                # It needs a session. Use the one passed to update_all_creatives.
                                result_dict = await get_creatives(
                                    creative_request=page_request_model,
                                    session=current_session  # Pass the session here
                                )

                                # Update search cursor for the next page of this combination
                                search_cursor_for_combo = result_dict.get("after")

                                if not search_cursor_for_combo and page_num < pages_to_cache - 1:
                                    logging.info(
                                        f"No more ads for current combination after page {page_num + 1}. Stopping caching for this combination.")
                                    break  # No more ads for this combination

                                await asyncio.sleep(
                                    0.5)  # Small delay between page fetches to avoid rate limits/overload

                            except Exception as e:
                                logging.error(
                                    f"Error caching combination {req_model.niche}/{req_model.country}/Page {page_num + 1}: {e}")
                                break  # Stop caching this combination on error

                    # Add the task to the list, ensure it's awaited by asyncio.gather later
                    combination_tasks.append(
                        _fetch_and_cache_pages_for_combination(creative_request_model, session)
                    )

                    # Use asyncio.gather to run all combination caching tasks concurrently
                    # This will wait for all of them to complete.
                logging.info(f"Launched {len(combination_tasks)} background caching tasks.")
                await asyncio.gather(*combination_tasks,
                                     return_exceptions=True)  # return_exceptions=True to see all errors
                logging.info("Finished one full cycle of background caching.")
