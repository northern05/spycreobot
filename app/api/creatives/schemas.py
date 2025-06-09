from pydantic import BaseModel, ConfigDict


class CreativeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str | None = None
    description: str | None = None
    body: str | None = None
    platforms: list
    url: str
    days_running: int
    page_id: str | None = None
    media_url: str


class CreativeResponse(CreativeBase):
    pass


class CreativeRequest(BaseModel):
    telegram_id: str
    niche: str
    placements: list
    country: str
    ad_type: str
    period: str
    keyword: str | None = None
    search_cursor: dict | None = None


class SimilarCreativeRequest(BaseModel):
    telegram_id: str
    country: str
    page_id: str
    niche: str
    search_cursor: dict | None = None
