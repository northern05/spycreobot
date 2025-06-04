from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.credits import dependencies as credits_dp
from app.core.models import db_helper
from .schemas import CreativeResponse, CreativeRequest
from app.core.modules_factory import fb_driver, redis_db


async def get_creatives(
        creative_request: CreativeRequest,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> dict:
    seen_ids_raw = await redis_db.smembers(f"user:{creative_request.telegram_id}:seen_ids")
    seen_ids = set(i.decode() for i in seen_ids_raw or [])

    ads, cursor = await fb_driver.search_ads_or(
        **creative_request.dict(exclude={"telegram_id"}),
        seen_ids=seen_ids
    )

    result = [CreativeResponse.model_validate(ad) for ad in ads]

    if result:
        await credits_dp.process_users_credits(session=session, telegram_id=creative_request.telegram_id)
        ad_ids = [ad["id"] for ad in ads]
        await redis_db.sadd(f"user:{creative_request.telegram_id}:seen_ids", *ad_ids)

    return {"ads": result, "after": cursor}
