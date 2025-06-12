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
    placements: list | None = None
    country: str | None = None
    ad_type: str | None = None
    period: str | None = None
    page_id: str | None = None
    keyword: str | None = None
    search_cursor: dict | None = None
