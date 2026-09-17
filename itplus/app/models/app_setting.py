"""Editable application settings (security, retention)."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from itplus.app.core.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(80), primary_key=True)
    value = Column(String(200), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    updated_by = Column(String(150), nullable=True)
