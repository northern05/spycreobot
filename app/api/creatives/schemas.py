from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CreativeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str | None = None
    description: str | None = None
    body: str | None = None
    platforms: list
    facebook_url: str
    days_running: int
    page_id: str | None = None
    media_url: str
    button: str | None = None
    app_url: str | None = None


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


class CreativeCreate(BaseModel):
    niche: str
    facebook_id: str
    title: str
    description: str
    platforms: list
    geo: str
    facebook_url: str
    created_at: datetime
    type: str
    page_id: str
    media_url: str
    app_url: str
    button: str | None = None
