from pydantic import BaseModel, ConfigDict


class Pin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    niche: str
    placements: list
    country: str
    ad_type: str
    period: str
    keyword: str


class PinCreate(Pin):
    pass


class PinResponse(Pin):
    id: int
