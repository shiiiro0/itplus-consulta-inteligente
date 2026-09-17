"""Roles and module permissions (RBAC)."""

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from itplus.app.core.database import Base

role_modules = Table(
    "role_modules",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "module_id",
        Integer,
        ForeignKey("system_modules.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(100), unique=True, nullable=False, index=True)

    modules = relationship(
        "SystemModule",
        secondary=role_modules,
        back_populates="roles",
    )
    users = relationship("User", back_populates="role_obj")


class SystemModule(Base):
    __tablename__ = "system_modules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(80), unique=True, nullable=False, index=True)
    label = Column(String(120), nullable=False)

    roles = relationship(
        "Role",
        secondary=role_modules,
        back_populates="modules",
    )
