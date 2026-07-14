from pydantic import BaseModel


class RolCreate(BaseModel):
    role_name: str
    sistemas: list[str] = []


class RolUpdate(BaseModel):
    role_name: str
    sistemas: list[str] = []


class SistemaItem(BaseModel):
    clave: str
    label: str


class RolItem(BaseModel):
    role_id: int
    role_name: str
    es_admin: bool
    usuarios: int
    sistemas: list[str]


class RolesListResponse(BaseModel):
    roles: list[RolItem]
    sistemas: list[SistemaItem]
