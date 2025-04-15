from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CreditsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    credits: int
    updated_at: datetime | None = None


class CreditsCreate(BaseModel):
    credits: int
    updated_at: datetime


class CreditsUpdate(CreditsBase):
    pass


class CreditsResponse(CreditsBase):
    pass


class ConnectTelegram(BaseModel):
    telegram_id: str
    wallet: str
