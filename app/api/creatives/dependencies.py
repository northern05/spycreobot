import asyncio
from datetime import datetime, timedelta
import json
from typing import Annotated
from fastapi import Path, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import errors
from app.api.credits import dependencies as credits_dp
from app.core.models import db_helper
from .schemas import CreativeResponse, CreativeBase, CreativeRequest
from app.core.modules_factory import redis_db, fb_driver


async def pin_creative_to_user(
        creative_data: CreativeBase,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> CreativeResponse:
    result = None
    return CreativeResponse.from_orm(result)


async def get_creatives(
        creative_request: CreativeRequest,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> list[CreativeResponse]:
    ads = await fb_driver.search_ads(**creative_request.dict(exclude={"telegram_id"}))
    result = [CreativeResponse.model_validate(ad) for ad in ads]
    if result:
        payment = await credits_dp.process_users_credits(session=session, telegram_id=creative_request.telegram_id)
    return result
