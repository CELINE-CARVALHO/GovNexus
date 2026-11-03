
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class Language(Base):
    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
    )

    english_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    native_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
