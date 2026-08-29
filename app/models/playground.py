from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Playground(Base):
    __tablename__ = "playground"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    share_code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    players: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    pin_hint: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    insights: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
