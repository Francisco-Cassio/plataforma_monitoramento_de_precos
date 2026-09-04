import enum
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.product import MonitoredProduct
    from app.models.alert import PriceAlert


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    REGULAR = "regular"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_roles"),
        default=UserRole.REGULAR,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relacionamentos (1 Usuário para N Produtos e N Alertas)
    products: Mapped[List["MonitoredProduct"]] = relationship(
        "MonitoredProduct",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[List["PriceAlert"]] = relationship(
        "PriceAlert",
        back_populates="user",
        cascade="all, delete-orphan",
    )