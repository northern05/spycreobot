from pydantic import BaseModel, ConfigDict


class CreativeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str | None = None
    description: str | None = None
    body: str | None = None
    platforms: list
    url: str
    days_running: int


class CreativeResponse(CreativeBase):
    pass


class CreativeRequest(BaseModel):
    telegram_id: str
    niche_keywords: list
    placements: list
    countries: list
    ad_type: str
    period: str
    keyword: str
    after: dict | None = None
