from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(
        validation_alias=AliasChoices("username", "email"),
        description="Usuario o correo electrónico",
    )
    password: str


class AzureLoginRequest(BaseModel):
    token: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    email: str
    rol: str
    permisos: list[str] = []


class MeResponse(BaseModel):
    username: str
    email: str
    rol: str
    permisos: list[str] = []
    nombre: str = ""


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    nombre: str
    rol: str
    activo: bool
    created_at: datetime

    model_config = {"from_attributes": True}
