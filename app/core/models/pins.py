from datetime import datetime
from sqlalchemy import String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Enum as SqlEnum
from enum import Enum

from .base import Base


class AdTypeEnum(str, Enum):
    image = "image"
    video = "video"
    all = "all"


class PeriodEnum(str, Enum):
    week = "week"
    month = "month"
    quarter = "quarter"
    halfyear = "halfyear"


class Pin(Base):
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)

    niche: Mapped[str] = mapped_column(String)
    placements: Mapped[list[str]] = mapped_column(ARRAY(String))
    country: Mapped[str] = mapped_column(String)
    ad_type: Mapped[AdTypeEnum] = mapped_column(SqlEnum(AdTypeEnum), nullable=False)
    period: Mapped[PeriodEnum] = mapped_column(SqlEnum(PeriodEnum), nullable=False)
    keyword: Mapped[str] = mapped_column(String)
