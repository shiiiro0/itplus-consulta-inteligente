"""SQLAlchemy database session and engine."""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from itplus.app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_users_table() -> None:
    """Add RBAC columns to legacy users table (idempotent)."""
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(150)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS nombre VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id INTEGER",
        "ALTER TABLE users ALTER COLUMN role DROP NOT NULL",
    ]
    with engine.connect() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        conn.commit()


def _migrate_documents_table() -> None:
    statements = [
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_type VARCHAR(50) DEFAULT 'upload'",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'general'",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS analyst_profile JSONB",
        "UPDATE documents SET source_type = 'upload' WHERE source_type IS NULL",
        "UPDATE documents SET category = 'general' WHERE category IS NULL",
    ]
    with engine.connect() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        conn.commit()


def _migrate_query_logs_table() -> None:
    statements = [
        "ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS chat_type VARCHAR(20)",
        "ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS custom_title VARCHAR(255)",
        "UPDATE query_logs SET chat_type = 'consulta' WHERE chat_type IS NULL",
    ]
    with engine.connect() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        conn.commit()


def _migrate_conversations_table() -> None:
    statements = [
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS title VARCHAR(255)",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ticket_reference VARCHAR(32)",
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS metadata JSONB",
    ]
    with engine.connect() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        conn.commit()


def init_db() -> None:
    """Create tables, enable pgvector, seed RBAC."""
    from itplus.app.models import (  # noqa: F401
        app_setting,
        conversation,
        document,
        query_log,
        role,
        user,
        user_session,
    )

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Base.metadata.create_all(bind=engine)
    _migrate_users_table()
    _migrate_documents_table()
    _migrate_query_logs_table()
    _migrate_conversations_table()

    db = SessionLocal()
    try:
        from itplus.app.services.rbac import seed_rbac
        from itplus.app.services import session_service, settings_service

        seed_rbac(db)
        months = settings_service.get_int(db, "sessions_retention_months")
        session_service.purge_old_sessions(db, months)
    finally:
        db.close()
