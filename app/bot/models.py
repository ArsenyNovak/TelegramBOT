from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, func, BigInteger, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = 'users'

    telegram_id: Mapped[int] = mapped_column(BigInteger,
                                             primary_key=True)  # Уникальный идентификатор пользователя в Telegram
    full_name: Mapped[str] = mapped_column(String, nullable=False)  # Имя пользователя
    username: Mapped[str] = mapped_column(String, nullable=True)  # Telegram username
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    bookkorts: Mapped[list["BookKort"]] = relationship("BookKort", back_populates="user")
    blacklist: Mapped[list["BlackList"]] = relationship("BlackList", back_populates="user")


class BookKort(Base):
    __tablename__ = 'bookkorts'

    bookkort_id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                            autoincrement=True)
    time_create: Mapped[datetime] = mapped_column(server_default=func.now())
    time_start: Mapped[datetime] = mapped_column(nullable=False)
    time_finish: Mapped[datetime] = mapped_column(nullable=False)
    time_update: Mapped[datetime] = mapped_column(server_default=func.now())
    canceled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    user: Mapped["User"] = relationship("User", back_populates="bookkorts")


class BlackList(Base):
    __tablename__ = 'blacklist'

    blacklist_id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                             autoincrement=True)
    time_start: Mapped[datetime] = mapped_column(server_default=func.now())
    time_finish: Mapped[datetime] = mapped_column(nullable=False)
    time_update: Mapped[datetime] = mapped_column(server_default=func.now())
    canceled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    user: Mapped["User"] = relationship("User", back_populates="blacklist")