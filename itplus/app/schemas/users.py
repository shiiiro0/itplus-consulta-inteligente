from typing import Any

from pydantic import BaseModel, EmailStr


class UsuarioCreate(BaseModel):
    nombre: str
    username: str
    correo: EmailStr
    password: str
    rol: str
    activo: bool = True


class UsuarioUpdate(BaseModel):
    nombre: str
    username: str
    correo: EmailStr
    rol: str
    activo: bool
    password: str | None = None


class UsuariosListResponse(BaseModel):
    data: list[dict[str, Any]]
    total: int
