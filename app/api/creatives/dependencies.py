from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.credits import dependencies as credits_dp
from app.core.models import db_helper
from .schemas import CreativeResponse, CreativeRequest, SimilarCreativeRequest
from app.core.modules_factory import fb_driver


async def get_creatives(
        creative_request: CreativeRequest,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> dict:
    ads, search_cursor = await fb_driver.get_ads_page(
        **creative_request.dict(exclude={"telegram_id"})
    )
    result = [CreativeResponse.model_validate(ad) for ad in ads]
    if result:
        await credits_dp.process_users_credits(session=session, telegram_id=creative_request.telegram_id)
    return {"ads": result, "after": search_cursor}
