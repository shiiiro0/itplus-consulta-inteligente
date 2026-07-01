from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    mime_type: str
    status: str
    error_message: str | None
    created_at: datetime
    indexed_at: datetime | None

    model_config = {"from_attributes": True}
