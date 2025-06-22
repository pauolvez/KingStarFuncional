from typing import Optional
from fastapi_users import schemas

# Esquema al crear usuario
class UserCreate(schemas.BaseUserCreate):
    role: Optional[str] = "vendedor"

# Esquema al leer usuario (respuesta)
class UserRead(schemas.BaseUser[int]):
    role: Optional[str]

# Esquema al actualizar
class UserUpdate(schemas.BaseUserUpdate):
    role: Optional[str]