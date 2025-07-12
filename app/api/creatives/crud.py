from enum import Enum
from datetime import datetime
from typing import Optional, List, get_args, get_origin

from sqlalchemy import select, func, or_, literal, any_
from fastapi_sa_orm_filter.main import FilterCore
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result
from fastapi import HTTPException
from pydantic import ValidationError, create_model

from .schemas import CreativeCreate, CreativeResponse
from app.core.models import Creative
from utils.paginated_response import PaginatedParams, paginate


class Operators(str, Enum):
    eq = "eq"
    ilike = "ilike"
    gte = "gte"
    lte = "lte"
    like = "like"
    in_ = "in_"
    between = "between"

    # ➕ кастомні оператори
    array_eq = "array_eq"
    array_ilike = "array_ilike"


creative_query_filters = {
    'created_at': [Operators.gte, Operators.lte, Operators.eq],
    'geo': [Operators.array_eq, Operators.array_ilike],
    'niche': [Operators.like, Operators.ilike],
    'page_id': [Operators.eq]
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
    print("Filter query raw:", filter_query)
    try:
        filter_inst = CreativeFilter(Creative, creative_query_filters)
        stmt = filter_inst.get_query(filter_query)
    except ValidationError as e:
        print("Pydantic validation error:", e.errors())
        raise HTTPException(status_code=400, detail=e.errors())
    except Exception as e:
        print("Unexpected error:", str(e))
        raise HTTPException(status_code=400, detail=str(e))
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
    creative = result.scalars().first()
    creative.state = "deleted"
    await session.commit()


class CreativeFilter(FilterCore):
    def _get_orm_for_field(self, column, operator, value):
        if operator == Operators.array_ilike.value:
            return or_(*[
                literal(v.lower()).ilike(any_(column))
                for v in value
            ])
        return super()._get_orm_for_field(column, operator, value)

    def _format_expression(self, column, operator, value: str) -> dict[str, any]:
        if operator in [Operators.array_eq.value, Operators.array_ilike.value]:
            return {column.name: value.split(",")}

        # fallback
        if operator not in [Operators.between.value, Operators.in_.value]:
            return {column.name: value.split(",")[0]}
        return {column.name: value.split(",")}

    def _get_optional_pydantic_model(self, pydantic_serializer, is_list: bool = False):
        fields = {}
        for k, v in pydantic_serializer.model_fields.items():
            origin_annotation = getattr(v, 'annotation')

            if get_origin(origin_annotation) is list:
                elem_type = get_args(origin_annotation)[0]
            elif hasattr(origin_annotation, '__origin__') and origin_annotation.__origin__ is list:
                elem_type = origin_annotation.__args__[0]
            else:
                elem_type = origin_annotation

            if is_list:
                fields[k] = (List[elem_type], None)
            else:
                fields[k] = (elem_type, None)

        return create_model(self.model.__name__, **fields)

    def _create_pydantic_serializer(self):
        fields = {}
        for column in self.model.__table__.columns:
            python_type = column.type.python_type
            name = column.name

            # Якщо колонка — масив (наприклад geo: list[str])
            if hasattr(column.type, 'item_type'):
                item_type = column.type.item_type.python_type
                fields[name] = (Optional[List[item_type]], None)
            else:
                fields[name] = (Optional[python_type], None)

        optional_model = create_model(f"{self.model.__name__}Optional", **fields)

        # 🔧 Фіксована логіка створення optional_list_model
        list_model_fields = {}
        for key, typ in fields.items():
            base_type = typ[0]
            if get_origin(base_type) is list:
                inner_type = get_args(base_type)[0]
                list_model_fields[key] = (List[inner_type], None)
            else:
                list_model_fields[key] = (List[base_type], None)

        optional_list_model = create_model(f"{self.model.__name__}List", **list_model_fields)

        return {
            "optional_model": optional_model,
            "optional_list_model": optional_list_model
        }
