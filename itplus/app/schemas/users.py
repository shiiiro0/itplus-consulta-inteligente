from typing import Any

from pydantic import BaseModel, EmailStr, Field

# Sin esto no había ninguna política mínima — se podía crear/actualizar un
# usuario con una contraseña vacía o de 1 caracter.
_MIN_PASSWORD_LENGTH = 8


class UsuarioCreate(BaseModel):
    nombre: str
    username: str
    correo: EmailStr
    password: str = Field(min_length=_MIN_PASSWORD_LENGTH)
    rol: str
    activo: bool = True


class UsuarioUpdate(BaseModel):
    nombre: str
    username: str
    correo: EmailStr
    rol: str
    activo: bool
    # Opcional: None significa "no cambiar la contraseña". Si se manda un
    # valor, sigue exigiéndose el mínimo.
    password: str | None = Field(default=None, min_length=_MIN_PASSWORD_LENGTH)


class UsuariosListResponse(BaseModel):
    data: list[dict[str, Any]]
    total: int
