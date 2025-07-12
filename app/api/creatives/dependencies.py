import logging
import asyncio
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
from utils.extra import extract_geo_from_filter
from utils.paginated_response import PaginatedResponse, PaginatedParams

CACHE_TTL_SECONDS = 3600

SEMAPHORE_LIMIT = 10

async def get_creatives(
        creative_request: CreativeRequest,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> dict:
    logging.info(f"DATA: {creative_request.dict()}")
    ads, search_cursor = await fb_driver.get_ads_page(
        **creative_request.dict(exclude={"telegram_id"})
    )
    result = [CreativeResponse.model_validate(ad) for ad in ads]
    if result:
        await credits_dp.process_users_credits(session=session, telegram_id=creative_request.telegram_id)
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
    else:
        geo = extract_geo_from_filter(objects_filter)
        res = await get_creatives(CreativeRequest(
            niche="gambling",
            placements=["instagram", "facebook", "audience_network", "threads", "messenger"],
            country=geo,
            ad_type="ALL",
            period="month")
        )
    return res


async def update_all_creatives():
    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)

    async def _fetch_and_cache_pages_for_combination(req_model: dict, pages_to_cache: int = 50):
        async with semaphore:
            search_cursor = None
            geo_value = req_model.get("country", "").lower()

            async with db_helper.session_factory() as current_session:
                for _ in range(pages_to_cache):
                    try:
                        req_model_with_cursor = {**req_model, "search_cursor": search_cursor}
                        ads, new_cursor = await fb_driver.get_ads_page(**req_model_with_cursor)

                        logging.info(f"[{geo_value}] Retrieved {len(ads)} ads.")

                        for ad in ads:
                            facebook_id = str(ad.get("id"))
                            media_id = ad.get("media_url")[-8:]

                            existing_creative = await crud.check_creative(
                                facebook_id=facebook_id,
                                media_unique_identifier=media_id
                            )

                            if not existing_creative:
                                await crud.create(
                                    session=current_session,
                                    creative_data=CreativeCreate(
                                        niche=req_model.get("niche"),
                                        facebook_id=facebook_id,
                                        title=ad.get("title"),
                                        description=ad.get("body"),
                                        platforms=ad.get("platforms"),
                                        geo=[geo_value],
                                        facebook_url=ad.get("facebook_url"),
                                        created_at=ad.get("created_at"),
                                        type=req_model.get("ad_type"),
                                        page_id=ad.get("page_id"),
                                        media_url=ad.get("media_url"),
                                        app_url=ad.get("app_url"),
                                        button=ad.get("button"),
                                        score=ad.get("score"),
                                        media_unique_identifier=media_id
                                    )
                                )
                            else:
                                current_geo = existing_creative.geo or []
                                if geo_value not in current_geo:
                                    existing_creative.geo = current_geo + [geo_value]

                        await current_session.commit()

                        if not new_cursor:
                            logging.info(f"[{geo_value}] No more ads to fetch.")
                            break

                        search_cursor = new_cursor

                    except Exception as e:
                        logging.exception(f"[{geo_value}] Error during caching: {e}")
                        break

    tasks = []

    for geo in COUNTRY_TO_KEYWORDS.keys():
        for ad_type in ("video", "image"):
            base_request_params = {
                "niche": "gambling",
                "placements": ["instagram", "facebook", "audience_network", "threads", "messenger"],
                "country": geo,
                "ad_type": ad_type,
                "period": "year",
                "page_size": 20
            }
            tasks.append(_fetch_and_cache_pages_for_combination(base_request_params))

    logging.info(f"Launching {len(tasks)} caching tasks with concurrency limit = {SEMAPHORE_LIMIT}...")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    logging.info("Finished all creative caching tasks.")

    return {"ok": True}


async def delete_ad(
        ad_id: Annotated[int, Path],
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    await crud.delete_ad(ad_id=ad_id, session=session)
    return {"ok": True}
