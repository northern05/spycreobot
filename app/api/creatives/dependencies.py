import logging
import hashlib
import json
from typing import Annotated

from fastapi import Depends, Path
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.credits import dependencies as credits_dp
from app.core.models import db_helper
from .schemas import CreativeResponse, CreativeRequest, CreativeCreate
from . import crud
from app.core.modules_factory import fb_driver, redis_db
from utils.const import *
from utils.paginated_response import PaginatedResponse, PaginatedParams

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
    return {"ads": result, "after": search_cursor}


async def get_all(
        telegram_id: str,
        objects_filter: str = Query(default=''),
        pagination_query: PaginatedParams = Depends(),
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    res = await crud.get_all(
        session=session, filter_query=objects_filter,
        pagination_query=pagination_query
    )
    if res:
        await credits_dp.process_users_credits(session=session, telegram_id=telegram_id)
    return res


async def update_all_creatives():
    async def _fetch_and_cache_pages_for_combination(
            req_model: dict, pages_to_cache: int = 10
    ):
        search_cursor = None
        async with db_helper.session_factory() as current_session:
            for page_num in range(pages_to_cache):
                try:
                    req_model_with_cursor = req_model.copy()
                    req_model_with_cursor["search_cursor"] = search_cursor

                    ads, new_cursor = await fb_driver.get_ads_page(**req_model_with_cursor)
                    print(f"{req_model.get('country')}, {len(ads)}")

                    for ad in ads:
                        existing_creative = await crud.check_creative(
                            session=current_session,
                            facebook_id=str(ad.get("id")),
                            media_unique_identifier=ad.get("media_url")[-8:]
                        )
                        if not existing_creative:
                            await crud.create(
                                session=current_session,
                                creative_data=CreativeCreate(
                                    niche=req_model.get("niche"),
                                    facebook_id=str(ad.get("id")),
                                    title=ad.get("title"),
                                    description=ad.get("body"),
                                    platforms=ad.get("platforms"),
                                    geo=req_model.get("country"),
                                    facebook_url=ad.get("facebook_url"),
                                    created_at=ad.get("created_at"),
                                    type=req_model.get("ad_type"),
                                    page_id=ad.get("page_id"),
                                    media_url=ad.get("media_url"),
                                    app_url=ad.get("app_url"),
                                    button=ad.get("button"),
                                    score=ad.get("score"),
                                    media_unique_identifier=ad.get("media_url")[-8:]
                                )
                            )

                    if not new_cursor:
                        logging.info(f"No more ads for combination {req_model}.")
                        break

                    search_cursor = new_cursor
                except Exception as e:
                    logging.exception(f"Error during caching for {req_model}: {e}")
                    break

    all_tasks = []
    for geo in COUNTRY_TO_KEYWORDS.keys():
        for ad_type in ("video", "image"):
            base_request_params = {
                "niche": "gambling",
                "placements": ["instagram", "facebook", "audience_network", "threads", "messenger"],
                "country": geo,
                "ad_type": ad_type,
                "period": "hour",
                "page_size": 50
            }
        # all_tasks.append(
        #     _fetch_and_cache_pages_for_combination(base_request_params, pages_to_cache=10)
        # )
            await _fetch_and_cache_pages_for_combination(req_model=base_request_params)

    logging.info(f"Launching {len(all_tasks)} background caching tasks.")
    # results = await asyncio.gather(*all_tasks, return_exceptions=True)
    # logging.info(f"Completed caching. Results: {results}")
    return {"ok": True}


async def delete_ad(
        ad_id: Annotated[int, Path],
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    await crud.delete_ad(ad_id=ad_id, session=session)
    return {"ok": True}
