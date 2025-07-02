from datetime import datetime
from sqlalchemy import String, Integer, ARRAY, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Creative(Base):
    niche: Mapped[str] = mapped_column(String, nullable=False)
    facebook_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    platforms: Mapped[list[str]] = mapped_column(ARRAY(String))
    geo: Mapped[str] = mapped_column(String, nullable=False)
    facebook_url: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    type: Mapped[str] = mapped_column(String, nullable=False)
    page_id: Mapped[str] = mapped_column(String, nullable=False)
    media_url: Mapped[str] = mapped_column(String, nullable=False)
    app_url: Mapped[str] = mapped_column(String)
    button: Mapped[str] = mapped_column(String)
    score: Mapped[int] = mapped_column(Integer)
    media_unique_identifier: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    def __repr__(self):
        return f"<Niche: {self.niche}, facebook_url {self.facebook_url}>"
