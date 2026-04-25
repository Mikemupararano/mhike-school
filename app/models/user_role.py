from __future__ import annotations

from sqlalchemy import Enum as SqlEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import UserRole


class UserRoleAssignment(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role", name="uq_user_roles_user_role"),
    )

    # You can keep this OR remove it (see note below)
    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[UserRole] = mapped_column(
        SqlEnum(
            UserRole,
            name="user_role_enum",  # ✅ FIXED (no collision)
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_roles",
        lazy="joined",  # ✅ better performance when accessing role.user
    )

    def __repr__(self) -> str:
        return f"<UserRoleAssignment user_id={self.user_id} role={self.role}>"
