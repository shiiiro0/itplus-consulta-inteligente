"""SQLAlchemy ORM models for ITPlus.

Importing any submodule of this package (e.g. ``itplus.app.models.document``)
first executes this ``__init__``, so every model below is always registered
with SQLAlchemy's declarative ``Base`` before the caller's specific import
runs. This matters for processes that only import a subset of the models
(e.g. the Celery worker importing only ``document``/``conversation``) but
still need cross-model foreign keys (like ``documents.uploaded_by`` ->
``users.id``) to resolve.
"""

from itplus.app.models import (  # noqa: F401
    app_setting,
    conversation,
    document,
    query_log,
    role,
    user,
    user_session,
)
