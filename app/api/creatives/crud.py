import re
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy import select, func, or_, and_
from fastapi_sa_orm_filter.main import FilterCore
from fastapi_sa_orm_filter.operators import Operators as ops
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result

from .schemas import CreativeCreate, CreativeResponse
from app.core.models import Creative
from utils.paginated_response import PaginatedParams, paginate

creative_query_filters = {
    'created_at': [ops.gte, ops.lte, ops.eq],
    'geo': [ops.ilike, ops.eq],
    'niche': [ops.like, ops.ilike],
    'page_id': [ops.eq]
}


async def create(session: AsyncSession, creative_data: CreativeCreate) -> Creative | None:
    creative = Creative(
        **creative_data.model_dump(),
    )
    session.add(creative)
    await session.commit()
    return creative


async def get_all(
        session: AsyncSession,
        filter_query: str,
        pagination_query: PaginatedParams,
):
    filter_inst = CreativeFilter(Creative, creative_query_filters)
    stmt = filter_inst.get_query(filter_query)

    response, data = await paginate(
        session=session, query=stmt,
        page_size=pagination_query.page_size, page_number=pagination_query.page_number
    )
    res = []
    for ad in data:
        days_running = (datetime.utcnow() - ad.created_at).days
        if days_running < 0: days_running = 0
        a = CreativeResponse.model_validate({
            **vars(ad),
            "days_running": days_running,
        })
        res.append(a)
    response["ads"] = res
    return response


async def check_creative(
        session: AsyncSession,
        facebook_id: str,
        media_unique_identifier: str
):
    stmt = select(Creative).filter(
        or_(
            Creative.facebook_id == facebook_id,
            Creative.media_unique_identifier == media_unique_identifier
        )
    )
    result: Result = await session.execute(stmt)
    return result.scalars().first()


async def delete_ad(
        session: AsyncSession,
        ad_id: int,
) -> None:
    stmt = (
        select(Creative)
        .filter(Creative.id == ad_id)
    )
    result: Result = await session.execute(stmt)
    pin = result.scalars().first()
    await session.delete(pin)
    await session.commit()


class CreativeFilter(FilterCore):

    def get_select_query_part(self):
        return (
            select(Creative).order_by(Creative.score.desc())
        )
