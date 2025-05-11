from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TransactionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    credits: int
    updated_at: datetime | None = None


class TransactionCreate(BaseModel):
    tx_hash: str
    asset: str
    amount: float
    created_at: datetime
    from_address: str
