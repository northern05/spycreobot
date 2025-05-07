from datetime import datetime
from sqlalchemy import Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Credits(Base):
    __tablename__ = "credits"
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=True, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self):
        return f"<User: {self.user_id}, credits {self.credits}>"
