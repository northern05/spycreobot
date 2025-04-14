from typing import Generic, TypeVar, List

from fastapi import Query
from pydantic import Field, BaseModel
from sqlalchemy import select, func, Select
from sqlalchemy.ext.asyncio import AsyncSession

M = TypeVar('M')


class PaginatedParams:
    def __init__(self, page_number: int = Query(1, ge=1), page_size: int = Query(10, ge=0, le=1001)):
        self.page_number = page_number
        self.page_size = page_size
        self.limit = page_size
        self.offset = (page_number - 1) * page_size


class PaginatedResponse(BaseModel, Generic[M]):
    page_size: int = Field(description='Number of items in data response')
    page_number: int = Field(description='Number of current page')
    total_items: int = Field(description='Total number of items in the response following given criteria')
    total_pages: int = Field(description='Total number of pages')
    data: List[M] = Field(description='List of items returned in the response following given criteria')


class Paginator:
    def __init__(self, session: AsyncSession, query: Select, page_number: int, page_size: int):
        self.session = session
        self.query = query
        self.page_number = page_number
        self.page_size = page_size
        self.limit = page_size
        self.offset = (page_number - 1) * page_size
        # computed later
        self.number_of_pages = 0

    async def get_response(self) -> tuple:
        return {
            'page_number': self.page_number,
            "total_items": await self._get_total_count(),
            'total_pages': self.number_of_pages,
            'page_size': self.page_size,
        }, [todo for todo in await self.session.scalars(self.query.limit(self.limit).offset(self.offset))]

    async def get_orm_response(self) -> tuple:
        data = self.query.limit(self.limit).offset(self.offset)
        res = await self.session.execute(data)
        return {
            'page_number': self.page_number,
            "total_items": await self._get_total_count(),
            'total_pages': self.number_of_pages,
            'page_size': self.page_size,
        }, res

    def _get_number_of_pages(self, count: int) -> int:
        rest = count % self.page_size
        quotient = count // self.page_size
        return quotient if not rest else quotient + 1

    async def _get_total_count(self) -> int:
        count = await self.session.scalar(select(func.count()).select_from(self.query.subquery()))
        self.number_of_pages = self._get_number_of_pages(count)
        return count


async def paginate(session: AsyncSession, query: Select, page_number: int, page_size: int, orm: bool = False) -> tuple:
    paginator = Paginator(session, query, page_number, page_size)
    return await paginator.get_response() if not orm else await paginator.get_orm_response()