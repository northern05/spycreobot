import datetime

from sqlalchemy import func, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    wallet: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    twitter_id: Mapped[str] = mapped_column(String(128), nullable=True, server_default="null")

    def __repr__(self):
        return f"<User[{self.id}] {self.wallet}>"
