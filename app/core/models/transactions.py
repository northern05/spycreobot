from datetime import datetime
from sqlalchemy import String, ForeignKey, func, Float
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Transaction(Base):
    tx_hash: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    asset: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self):
        return f"<User[{self.user_id}] {self.tx_hash}, amount: {self.amount} {self.asset}>"
