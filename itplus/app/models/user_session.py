"""Active session registry for monitoring and revocation."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String

from itplus.app.core.database import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    jti = Column(String(40), primary_key=True)
    username = Column(String(150), nullable=False, index=True)
    login_method = Column(String(10), nullable=False, default="local")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(400), nullable=True)
    device_id = Column(String(64), nullable=True)
    revoked = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
