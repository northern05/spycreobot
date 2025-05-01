from pydantic import BaseModel, ConfigDict


class CreativeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    days_running: int


class CreativeResponse(CreativeBase):
    pass


class CreativeRequest(BaseModel):
    niche: list
    placements: list
    countries: list
    ad_type: str
    period: str
    keywords: str
