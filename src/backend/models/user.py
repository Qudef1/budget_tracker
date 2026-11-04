from enum import Enum as PyEnum
from sqlalchemy import Boolean, Enum, String, text
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base

class UserRole(str, PyEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="userrole"), nullable=False, default=UserRole.USER, server_default="USER")
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
