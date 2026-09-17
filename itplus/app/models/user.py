import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from itplus.app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(150), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    nombre = Column(String(255), nullable=False, default="")
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True, index=True)
    # Legacy column kept for migration compatibility; prefer role_obj.role_name.
    role = Column(String(50), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    role_obj = relationship("Role", back_populates="users")

    @property
    def rol_name(self) -> str:
        if self.role_obj and self.role_obj.role_name:
            return self.role_obj.role_name
        legacy = (self.role or "").strip()
        if legacy.lower() in ("admin", "administrador"):
            return "Administrador"
        return legacy or "Usuario"
