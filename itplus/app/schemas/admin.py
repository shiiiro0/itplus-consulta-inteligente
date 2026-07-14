from pydantic import BaseModel


class RevokeSessionRequest(BaseModel):
    jti: str


class SettingsUpdate(BaseModel):
    values: dict[str, int]
